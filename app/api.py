from app import app, db, utils
from flask import render_template, request

from app.models import NewLecturer, EditLecturer, Tag
from pydantic import ValidationError
from typing import List, Dict, Any
import uuid
import json
from bson import json_util
import bleach

DEFAULT_RESULTS_COUNT = 20


lecturers = db.lecturers
reservations = db.reservations
tags = db.tags

ALLOWED_TAGS = ['b', 'i', 'u', 'em', 'strong', 'a']


@app.route("/api")
def api():
    return {"secret":"The cake is a lie"}


@app.route("/api/lecturers", methods=["GET", "POST"])
def api_lecturers():
    if request.method == 'POST':
        request_json = request.get_json()
        try:
            # Validate by creating lecturer object
            new_lecturer_object = NewLecturer(**request_json)

            # Load existing tags as {name: uuid} json
            existing_tags: Dict[str, str] = dict()
            for tag in list(tags.find()):
                tag["uuid"] = str(tag.pop("_id"))
                existing_tags[tag["name"]] = tag["uuid"]

            # Check tags in request
            # Find/create and ADD uuid
            for i in range(len(new_lecturer_object.tags)):

                if new_lecturer_object.tags[i].name in existing_tags.keys():
                    # Existing tag was found
                    new_lecturer_object.tags[i].uuid = str(existing_tags[new_lecturer_object.tags[i].name])

                else:
                    # New tag will be created
                    new_lecturer_object.tags[i].uuid = str(uuid.uuid4())

                    new_tag_json = Tag(uuid=new_lecturer_object.tags[i].uuid, name=new_lecturer_object.tags[i].name).model_dump()
                    
                    # Renamed uuid to _id
                    new_tag_json["_id"] = new_tag_json.pop("uuid")
                    tags.insert_one(new_tag_json)

            new_lecturer_json = new_lecturer_object.model_dump()

            # Escape unsafe HTML
            new_lecturer_json = {k: bleach.clean(v, tags=ALLOWED_TAGS, strip=True) if isinstance(v, str) else v for k, v in new_lecturer_json.items()}

            new_lecturer_json["_id"] = str(uuid.uuid4())
            lecturers.insert_one(new_lecturer_json)

            reserved_hours = dict()
            reserved_hours["_id"] = new_lecturer_json["_id"]
            reserved_hours["teaching_hours"] = { str(hour): {"reserved": False, "client_email": None, "client_phone": None} for hour in range(8, 21) }
            reservations.insert_one(reserved_hours)

            return get_specific_lecturer(new_lecturer_json["_id"])

        except ValidationError as e:
            # Validation not successfull
            return {"code": 400, "message": "Invalid data"}, 400
    
    # Renaming keys "_id" to "uuid"
    found_lecturers: List[Dict[str, Any]] = list(lecturers.find())
    for i in range(len(found_lecturers)):
        found_lecturers[i]['uuid'] = found_lecturers[i].pop('_id')

    return json.loads(json_util.dumps(found_lecturers)), 200


@app.route("/api/lecturers/<string:uuid>", methods=["GET"])
def get_specific_lecturer(uuid: str):
    found_lecturer = lecturers.find_one({"_id": {"$eq": uuid}})

    if found_lecturer is None:
        return {"code": 404, "message": "User not found"}, 404
    else:
        found_lecturer["uuid"] = found_lecturer.pop("_id")
        return json.loads(json_util.dumps(found_lecturer)), 200


@app.route("/api/lecturers/<string:uuid>", methods=["DELETE"])
def delete_lecturer(uuid):
    deleted = bool(lecturers.delete_one({"_id": {"$eq": uuid}}).deleted_count)

    if deleted:
        return '', 204
    else:
        return {"code": 404, "message": "User not found"}, 404


@app.route("/api/lecturers/<string:lecturer_uuid>", methods=["PUT"])
def update_lecturer(lecturer_uuid):
    lecturer_exists = bool(lecturers.find_one({"_id": {"$eq": lecturer_uuid}}))

    if lecturer_exists:
        updated_json = request.get_json()

        try:
            updated_lecturer_object = EditLecturer(**updated_json)

            if updated_lecturer_object.tags is not None:
                existing_tags: Dict[str, str] = dict()
                for tag in list(tags.find()):
                    tag["uuid"] = str(tag.pop("_id"))
                    existing_tags[tag["name"]] = tag["uuid"]

                # Check tags in request
                # Find/create and ADD uuid
                for i in range(len(updated_lecturer_object.tags)):
                    if updated_lecturer_object.tags[i].name in existing_tags.keys():
                        # Existing tag was found
                        updated_lecturer_object.tags[i].uuid = str(existing_tags[updated_lecturer_object.tags[i].name])

                    else:
                        # New tag will be created
                        updated_lecturer_object.tags[i].uuid = str(uuid.uuid4())

                        new_tag_json = Tag(uuid=updated_lecturer_object.tags[i].uuid, name=updated_lecturer_object.tags[i].name).model_dump()
                        
                        # Renamed uuid to _id
                        new_tag_json["_id"] = new_tag_json.pop("uuid")
                        tags.insert_one(new_tag_json)

            updated_lecturer_json = updated_lecturer_object.model_dump(exclude_none=True)

            # Escape unsafe HTML
            updated_lecturer_json = {k: bleach.clean(v, tags=ALLOWED_TAGS, strip=True) if isinstance(v, str) else v for k, v in updated_lecturer_json.items()}
            
            lecturers.update_one({"_id": lecturer_uuid}, {"$set": updated_lecturer_json})
            return get_specific_lecturer(lecturer_uuid)
        
        except ValidationError as e:
            return {"code": 400, "message": "Invalid data"}, 400
        
    else:
        return {"code": 404, "message": "User not found"}, 404


@app.route("/api/filter", methods=["GET"])
def filter_lecturers():
    # cost_min
    # cost_max
    # tags[] -> "tag1,tag2,tag3".split(',')
    # location

    # start_index
    # total_count

    search_query = dict()

    location = request.args.get('location')
    if location:
        search_query["location"] = {"$eq": location}

    price_conditions = []
    cost_min = request.args.get('cost_min')
    if cost_min is not None:
        if cost_min.isdecimal():
            price_conditions.append({"price_per_hour": {"$gte": int(cost_min)}})

    cost_max = request.args.get('cost_max')
    if cost_max is not None:
        if cost_max.isdecimal():
            price_conditions.append({"price_per_hour": {"$lte": int(cost_max)}})

    if price_conditions:
        search_query["$and"] = price_conditions

    tags = request.args.getlist('tag')
    if tags:
        # Ensure all tags are valid UUIDs
        for tag in tags:
            try:
                uuid.UUID(tag, version=4)
            except ValueError:
                return "Invalid tag id", 400
        search_query["tags.uuid"] = {"$all": tags}


    start_index = request.args.get('start_index')
    if start_index is not None:
        if start_index.isdecimal():
            start_index = int(start_index)
        else:
            start_index = 0
    else:
        start_index = 0
    
    total_count = request.args.get('total_count')
    if total_count is not None:
        if total_count.isdecimal():
            total_count = int(total_count)
        else:
            total_count = DEFAULT_RESULTS_COUNT
    else:
        total_count = DEFAULT_RESULTS_COUNT

    found_lecturers: List[Dict[str, Any]] = list(lecturers.find(search_query).skip(start_index).limit(total_count))

    # Renaming keys "_id" to "uuid" 
    for i in range(len(found_lecturers)):
        found_lecturers[i]['uuid'] = found_lecturers[i].pop('_id')

    # return json.loads(json_util.dumps(found_lecturers)), 200
    return render_template(
        "lecturer_list.html", 
        lecturers=found_lecturers, 
        start_index=start_index, 
        total_count=total_count, 
        query_string=request.query_string.decode("utf-8"))


# reservation API
@app.route("/api/reservation/<string:uuid>", methods=["GET", "POST", "DELETE"])
def reservation_system(uuid):

    uuid_exists = bool(reservations.find_one({"_id": {"$eq": uuid}}))
    if not uuid_exists:
        return {"code": 404, "message": "User not found"}, 404

    if request.method == 'GET':
        # get lecturer's info about reserved hours

        found_reservations = reservations.find_one({"_id": {"$eq": uuid}})
        
        try:
            teaching_hours = json.loads(json_util.dumps(found_reservations))["teaching_hours"]
            return teaching_hours, 200
        
        except:
            return {"code": 404, "message": "User not found"}, 404


    elif request.method == 'POST':
        # post client reservation details and selected time
        request_json: Dict = request.get_json() # {"hour": "8", "email": "test@example.com", "phone": "+420123456789"}

        # time validation
        hour = request_json.get("hour")
        if hour is not None:
            try:
                converted_time = int(hour)
                if not (converted_time >= 8 and converted_time <= 20):
                    return {"code": 400, "message": "Time not in a range"}, 400
                
            except:
                return {"code": 400, "message": "Invalid data"}, 400
        else:
            return {"code": 400, "message": "Invalid data"}, 400
        

        lecturer_hours_info = reservations.find_one({"_id": {"$eq": uuid}})["teaching_hours"]
        hour_info = lecturer_hours_info.get(str(converted_time))

        if hour_info is None:
            return {"code": 400, "message": "Time not available"}, 400
        
        already_reserved = bool(hour_info.get("reserved"))

        if already_reserved:
            return {"code": 400, "message": "Time already taken"}, 400
        

        # email validation
        email = request_json.get("email")
        if email is None:
            return {"code": 400, "message": "Invalid data"}, 400
        else:
            email = str(email).strip()
        
        if not utils.is_email_valid(email):
            return {"code": 400, "message": "Invalid email"}, 400

        # phone number validation
        phone = request_json.get("phone")
        if phone is None:
            return {"code": 400, "message": "Invalid data"}, 400
        else:
            phone = str(phone).replace(' ', '')

        if not utils.is_phone_number_valid(phone):
            return {"code": 400, "message": "Invalid number"}, 400

        reservations.update_one({"_id": uuid, f"teaching_hours.{str(converted_time)}": {"$exists": True}}, {"$set": {
            f"teaching_hours.{str(converted_time)}.reserved": True,
            f"teaching_hours.{str(converted_time)}.client_email": email,
            f"teaching_hours.{str(converted_time)}.client_phone": phone}})


        return {"code": 200, "message": "Success"}, 200
    
    elif request.method == 'DELETE':
        # reset reserved time

        request_json: Dict = request.get_json() # {"hour": "8"}

        # time validation
        hour = request_json.get("hour")
        if hour is not None:
            try:
                converted_time = int(hour)
                if not (converted_time >= 8 and converted_time <= 20):
                    return {"code": 400, "message": "Time not in a range"}, 400
                
            except:
                return {"code": 400, "message": "Invalid data"}, 400
        else:
            return {"code": 400, "message": "Invalid data"}, 400

        reservations.update_one({"_id": uuid, f"teaching_hours.{str(converted_time)}": {"$exists": True}}, {"$set": {
                f"teaching_hours.{str(converted_time)}.reserved": False,
                f"teaching_hours.{str(converted_time)}.client_email": None,
                f"teaching_hours.{str(converted_time)}.client_phone": None
            }}
        )

        return {"code": 200, "message": "Success"}, 200

    else:
        return {"code": 404, "message": "User not found"}, 404
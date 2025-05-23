from app import app, db, utils
from flask import render_template, request, session, redirect, abort, Response

from app.models import NewLecturer, EditLecturer, Tag
from pydantic import ValidationError
from typing import List, Dict, Any
import uuid
import json
from bson import json_util
import bleach
from functools import wraps
from werkzeug.security import check_password_hash, generate_password_hash
import icalendar
from datetime import datetime

DEFAULT_RESULTS_COUNT = 20


lecturers = db.lecturers
reservations = db.reservations
tags = db.tags
credentials = db.credentials

ALLOWED_TAGS = ['b', 'i', 'u', 'em', 'strong', 'a']

users = {
    "TdA": generate_password_hash("d8Ef6!dGG_pv"),
    "localAPI": generate_password_hash("863ba71ec174153fb80210189118a591")
}

def authenticate(username, password):
    if username in users and check_password_hash(users[username], password):
        return True
    return False

def requires_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.authorization
        if not auth or not authenticate(auth.username, auth.password):
            abort(401)
        return f(*args, **kwargs)
    return decorated



@app.route("/api")
@requires_auth
def api():
    return {"secret":"The cake is a lie"}


@app.route("/api/lecturers", methods=["GET", "POST"])
@requires_auth
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
            
            username = new_lecturer_json.get("username", "").strip()
            password = new_lecturer_json.get("password", "").strip()

            if username == '' or password == '':
                return {"code": 400, "message": "Invalid username or password"}, 400

            utils.add_user_to_reservations_db(new_lecturer_json["_id"])
            utils.add_user_credentials_to_db(new_lecturer_json["_id"], username, password)
            
            # remove credentials from public JSON!
            new_lecturer_json.pop("username")
            new_lecturer_json.pop("password")
            lecturers.insert_one(new_lecturer_json)


            return get_specific_lecturer(new_lecturer_json["_id"])

        except ValidationError as e:
            # Validation not successfull
            return {"code": 400, "message": "Invalid data"}, 400
    
    # Renaming keys "_id" to "uuid"
    found_lecturers: List[Dict[str, Any]] = list(lecturers.find())
    for i in range(len(found_lecturers)):
        found_lecturers[i]['uuid'] = found_lecturers[i].pop('_id')

    return json.loads(json_util.dumps(found_lecturers)), 200


@app.route("/api/lecturers/<string:lecturer_uuid>", methods=["GET"])
@requires_auth
def get_specific_lecturer(lecturer_uuid: str):
    return utils.get_specific_lecturer(lecturer_uuid)


@app.route("/api/lecturers/<string:lecturer_uuid>", methods=["DELETE"])
@requires_auth
def delete_lecturer(lecturer_uuid):
    success_lecturers = utils.delete_user_from_lecturers_db(lecturer_uuid)
    success_reservations = utils.delete_user_from_reservations_db(lecturer_uuid)
    success_credentials = utils.delete_user_from_credentials_db(lecturer_uuid)

    if success_lecturers and success_reservations and success_credentials:
        return {"code": 204, "message": "Success"}, 204
    else:
        return {"code": 404, "message": "User not found"}, 404


@app.route("/api/lecturers/<string:lecturer_uuid>", methods=["PUT"])
@requires_auth
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

            # check for credentials change
            new_username = updated_lecturer_json.get("username")
            if new_username is not None:
                updated_lecturer_json.pop("username")
                success = utils.change_user_username_in_db(lecturer_uuid, new_username)
                
                if not success:
                    return {"code": 400, "message": "Username already exists in DB!"}, 400

            new_password = updated_lecturer_json.get("password")
            if new_password is not None:
                updated_lecturer_json.pop("password")
                success = utils.change_user_password_in_db(lecturer_uuid, new_password)

                if not success:
                    return {"code": 400, "message": "Failed to change a password!"}, 400


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
@app.route("/api/reservation/<string:lecturer_uuid>", methods=["GET", "POST", "DELETE"])
def reservation_system(lecturer_uuid):

    uuid_exists = bool(reservations.find_one({"_id": {"$eq": lecturer_uuid}}))
    if not uuid_exists:
        return {"code": 404, "message": "User not found"}, 404

    if request.method == 'GET':
        # get lecturer's info only about hours

        found_reservations = reservations.find_one({"_id": {"$eq": lecturer_uuid}})
        
        try:
            teaching_dates = found_reservations.get("teaching_dates")
            for date in teaching_dates:
                for hour in teaching_dates[date]:
                    del teaching_dates[date][hour]['client_email']
                    del teaching_dates[date][hour]['client_phone']

            return teaching_dates, 200
        
        except:
            return {"code": 404, "message": "User not found"}, 404


    elif request.method == 'POST':
        # book a time (client)
        request_json: Dict = request.get_json() # {"date": "2024-02-28", "hour": "8", "email": "test@example.com", "phone": "+420123456789"}

        # date validation
        reservation_date: str = request_json.get("date") # yyyy-mm-dd

        if not utils.is_date_valid(reservation_date):
            return {"code": 400, "message": "Invalid data"}, 400

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
        

        found_reservations = reservations.find_one({"_id": {"$eq": lecturer_uuid}})
        teaching_dates = found_reservations.get("teaching_dates", {})

        lecturer_hours_info = teaching_dates.get(reservation_date, {})
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

        reservations.update_one({"_id": lecturer_uuid, f"teaching_dates.{reservation_date}.{str(converted_time)}": {"$exists": True}}, {"$set": {
            f"teaching_dates.{reservation_date}.{str(converted_time)}.reserved": True,
            f"teaching_dates.{reservation_date}.{str(converted_time)}.client_email": email,
            f"teaching_dates.{reservation_date}.{str(converted_time)}.client_phone": phone}})


        return {"code": 200, "message": "Success"}, 200

    return {"code": 405, "message": "Method not allowed"}, 405


# reservation API for lecturers
@app.route("/api/reservation-admin/", methods=["GET", "POST", "DELETE", "PUT"])
def reservation_system_admin():

    # Check login status
    if not bool(session.get("logged_in")):
        return redirect("/lecturer-login")

    lecturer_uuid = session.get("lecturer_uuid")

    if lecturer_uuid is None:
        return {"code": 404, "message": "User not found"}, 404

    uuid_exists = bool(reservations.find_one({"_id": {"$eq": lecturer_uuid}}))
    if not uuid_exists:
        return {"code": 404, "message": "User not found"}, 404


    if request.method == 'GET':
        # get full info about lecturer's reserved hours

        found_reservations = reservations.find_one({"_id": {"$eq": lecturer_uuid}})
        
        try:
            teaching_dates = found_reservations.get("teaching_dates", {})
            return teaching_dates, 200
        
        except:
            return {"code": 404, "message": "User not found"}, 404


    elif request.method == 'POST':
        # add time to available times

        request_json: Dict = request.get_json() # {"date": "2024-02-28","hours": ["8", "10"]}

        # date validation
        reservation_date: str = request_json.get("date") # yyyy-mm-dd

        if not utils.is_date_valid(reservation_date):
            return {"code": 400, "message": "Invalid data"}, 400

        # time validation
        hours: list = request_json.get("hours")
        if hours is not None:
            for hour in hours:
                try:
                    converted_time = int(hour)
                    if not (converted_time >= 8 and converted_time <= 20):
                        return {"code": 400, "message": "Time not in a range"}, 400
                    
                except:
                    return {"code": 400, "message": "Invalid data"}, 400
        else:
            return {"code": 400, "message": "Invalid data"}, 400


        # every hour
        for hour in hours:
            reservations.update_one({"_id": lecturer_uuid, f"teaching_dates.{reservation_date}.{int(hour)}": {"$exists": False}}, {"$set": {
                    f"teaching_dates.{reservation_date}.{int(hour)}.reserved": False,
                    f"teaching_dates.{reservation_date}.{int(hour)}.client_email": None,
                    f"teaching_dates.{reservation_date}.{int(hour)}.client_phone": None
                }}
            )

        return {"code": 200, "message": "Success"}, 200

    
    elif request.method == 'DELETE':
        # remove time from available times
        
        request_json: Dict = request.get_json() # {"date": "2024-02-28","hours": ["8", "10"]}

        # date validation
        reservation_date: str = request_json.get("date") # yyyy-mm-dd

        if not utils.is_date_valid(reservation_date):
            return {"code": 400, "message": "Invalid data"}, 400

        # time validation
        hours: list = request_json.get("hours")
        if hours is not None:
            for hour in hours:
                try:
                    converted_time = int(hour)
                    if not (converted_time >= 8 and converted_time <= 20):
                        return {"code": 400, "message": "Time not in a range"}, 400
                    
                except:
                    return {"code": 400, "message": "Invalid data"}, 400
        else:
            return {"code": 400, "message": "Invalid data"}, 400

        # delete every hour in list
        for hour in hours:
            reservations.update_one(
                {"_id": {"$eq": lecturer_uuid}, f"teaching_dates.{reservation_date}.{int(hour)}": {"$exists": True}},
                {"$unset": {f"teaching_dates.{reservation_date}.{int(hour)}": 1}}
            )

        # delete date in DB if there is no other reservation
        lecturer_reservations = reservations.find_one({"_id": {"$eq": lecturer_uuid}})
        if lecturer_reservations is not None:
            teaching_dates = lecturer_reservations.get("teaching_dates", {})
            if not teaching_dates.get(reservation_date):
                reservations.update_one(
                    {"_id": {"$eq": lecturer_uuid}, f"teaching_dates.{reservation_date}": {"$exists": True}},
                    {"$unset": {f"teaching_dates.{reservation_date}": 1}}
            )

        return {"code": 200, "message": "Success"}, 200
    

    elif request.method == 'PUT':
        # reset any reserved time

        request_json: Dict = request.get_json() # {"date": "2024-02-28","hours": ["8", "10"]}

        # date validation
        reservation_date: str = request_json.get("date") # yyyy-mm-dd

        if not utils.is_date_valid(reservation_date):
            return {"code": 400, "message": "Invalid data"}, 400

        # time validation
        hours: list = request_json.get("hours")
        if hours is not None:
            for hour in hours:
                try:
                    converted_time = int(hour)
                    if not (converted_time >= 8 and converted_time <= 20):
                        return {"code": 400, "message": "Time not in a range"}, 400
                    
                except:
                    return {"code": 400, "message": "Invalid data"}, 400
        else:
            return {"code": 400, "message": "Invalid data"}, 400

        # reset every hour in list
        for hour in hours:
            reservations.update_one(
                {"_id": lecturer_uuid, f"teaching_dates.{reservation_date}.{int(hour)}": {"$exists": True}},
                {"$set": {
                    f"teaching_dates.{reservation_date}.{int(hour)}.reserved": False,
                    f"teaching_dates.{reservation_date}.{int(hour)}.client_email": None,
                    f"teaching_dates.{reservation_date}.{int(hour)}.client_phone": None
                }}
            )

        return {"code": 200, "message": "Success"}, 200


    return {"code": 405, "message": "Method not allowed"}, 405

# reservation API for lecturers
@app.route("/api/admin-download-ical/", methods=["GET"])
def admin_download_ical():
    # Check login status
    if not bool(session.get("logged_in")):
        return redirect("/lecturer-login")

    lecturer_uuid = session.get("lecturer_uuid")

    if lecturer_uuid is None:
        return {"code": 404, "message": "User not found"}, 404

    uuid_exists = bool(reservations.find_one({"_id": {"$eq": lecturer_uuid}}))
    if not uuid_exists:
        return {"code": 404, "message": "User not found"}, 404


    if request.method == 'GET':
        # download .ical with lecturer's reserved hours

        new_cal = icalendar.Calendar()
        new_cal.add('version', '2.0')

        found_reservations = reservations.find_one({"_id": {"$eq": lecturer_uuid}})
        teaching_dates = found_reservations.get("teaching_dates", {})

        for teaching_date in teaching_dates:
            teaching_hours = teaching_dates.get(teaching_date, {})

            for hour in teaching_hours:
                hour_info = teaching_hours.get(hour, {})
                reserved = bool(hour_info.get("reserved", False))

                if reserved:
                    start_hour = int(hour)

                    splitted_start_date = teaching_date.split("-")
                    start_day = int(splitted_start_date[2])
                    start_month = int(splitted_start_date[1])
                    start_year = int(splitted_start_date[0])

                    client_email = hour_info.get("client_email", "")
                    client_phone = hour_info.get("client_phone", "")

                    event = icalendar.Event()
                    event.add('summary', 'Doučování')
                    event.add('description', f'Kontakt na klienta:\n{client_email}\n{client_phone}')
                    event.add('dtstart', datetime(start_year, start_month, start_day, start_hour, 0, 0))
                    event.add('dtend', datetime(start_year, start_month, start_day, start_hour+1, 0, 0))

                    # add event to the calendar
                    new_cal.add_component(event)
        
        # count number of events
        if len(new_cal.walk('VEVENT')) > 0:
            response = Response(new_cal.to_ical(), mimetype="text/calendar")

            filename = datetime.now().strftime('%Y-%m-%d') + '_plan-vyuky.ics'
            response.headers.add("Content-Disposition", "attachment", filename=filename)

            return response, 200

        else:
            # calendar is empty
            return "", 200


    return {"code": 405, "message": "Method not allowed"}, 405


@app.route("/api/change-password/", methods=["PUT"])
def change_password():

    # Check login status
    if not bool(session.get("logged_in")):
        return redirect("/lecturer-login")

    lecturer_uuid = session.get("lecturer_uuid")

    if lecturer_uuid is None:
        return {"code": 404, "message": "User not found"}, 404

    uuid_exists = bool(credentials.find_one({"_id": {"$eq": lecturer_uuid}}))
    if not uuid_exists:
        return {"code": 404, "message": "User not found"}, 404


    if request.method == 'PUT':
        request_json: Dict = request.get_json() # {"old_password": "", "new_password": ""}

        old_password = request_json.get("old_password")
        new_password = request_json.get("new_password")

        if old_password == new_password:
            return {"code": 200, "message": "Passwords are same"}, 200
        
        lecturer = credentials.find_one({"_id": {"$eq": lecturer_uuid}})
        old_hashed_password = lecturer.get("hashed_password")

        if not utils.check_hash_bcrypt(old_password, old_hashed_password):
            return {"code": 400, "message": "Wrong password!"}, 400

        succesfuly_changed = utils.change_user_password_in_db(lecturer_uuid, new_password)

        if succesfuly_changed:
            return {"code": 200, "message": "Password change success"}, 200
        else:
            return {"code": 400, "message": "Unkown error when changing password"}, 400

    return {"code": 405, "message": "Method not allowed"}, 405

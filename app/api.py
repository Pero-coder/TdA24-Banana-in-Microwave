from turtle import up
from app import app, db
from flask import request

from app.models import NewLecturer, EditLecturer, Tag
from pydantic import ValidationError
from typing import List, Dict, Any
import uuid
import json
from bson import json_util
import html

lecturers = db.lecturers
tags = db.tags


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
            for i in range(len(new_lecturer_object.tags)):

                if new_lecturer_object.tags[i].name in existing_tags.keys():
                    # Existing tag uuid
                    new_lecturer_object.tags[i].uuid = str(existing_tags[new_lecturer_object.tags[i].name])

                else:
                    # New uuid tag
                    new_lecturer_object.tags[i].uuid = str(uuid.uuid4())

                    new_tag_json = Tag(uuid=new_lecturer_object.tags[i].uuid, name=new_lecturer_object.tags[i].name).model_dump()
                    
                    # Renamed uuid to _id
                    new_tag_json["_id"] = new_tag_json.pop("uuid")
                    tags.insert_one(new_tag_json)

            new_lecturer_json = new_lecturer_object.model_dump()

            # Escape HTML
            new_lecturer_json = {k: html.escape(v) if isinstance(v, str) else v for k, v in new_lecturer_json.items()}

            new_lecturer_json["_id"] = str(uuid.uuid4())
            lecturers.insert_one(new_lecturer_json)

        except ValidationError as e:
            # Validation not successfull
            print(e)
            pass
    
    # Renaming keys "_id" to "uuid" 
    found_lecturers: List[Dict[str, Any]] = list(lecturers.find())
    for i in range(len(found_lecturers)):
        found_lecturers[i]['uuid'] = found_lecturers[i].pop('_id')

    return json.loads(json_util.dumps(found_lecturers))


@app.route("/api/lecturers/<string:uuid>", methods=["GET"])
def get_specific_lecturer(uuid: str):
    found_lecturer = lecturers.find_one({"_id": uuid})

    if found_lecturer is None:
        return {"code": 404, "message": "User not found"}, 404
    else:
        found_lecturer["uuid"] = found_lecturer.pop("_id")
        return json.loads(json_util.dumps(found_lecturer)), 200


@app.route("/api/lecturers/<string:uuid>", methods=["DELETE"])
def delete_lecturer(uuid):
    deleted = bool(lecturers.delete_one({"_id": uuid}).deleted_count)

    if deleted:
        return '', 204
    else:
        return {"code": 404, "message": "User not found"}, 404


@app.route("/api/lecturers/<string:uuid>", methods=["PUT"])
def update_lecturer(uuid):
    lecturer_exists = bool(lecturers.find_one({"_id": uuid}))

    if lecturer_exists:
        updated_json = request.get_json()

        try:
            updated_lecturer_json = EditLecturer(**updated_json).model_dump(exclude_none=True)

            # Escape HTML
            updated_lecturer_json = {k: html.escape(v) if isinstance(v, str) else v for k, v in updated_lecturer_json.items()}
            
            lecturers.update_one({"_id": uuid}, {"$set": updated_lecturer_json})
            return get_specific_lecturer(uuid)
        
        except ValidationError as e:
            return {"code": 400, "message": "Invalid data"}, 400
        
    else:
        return {"code": 404, "message": "User not found"}, 404

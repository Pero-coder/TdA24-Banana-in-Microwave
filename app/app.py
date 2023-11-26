import os
import json
from bson import json_util, ObjectId
from dotenv import load_dotenv
from flask import Flask, render_template, request
from pymongo.mongo_client import MongoClient
from pydantic import ValidationError
import uuid
from typing import List, Dict, Any

from validation_templates import NewLecturer, EditLecturer



load_dotenv()
client = MongoClient(
    f'mongodb+srv://{os.environ.get("MONGO_USERNAME")}:{os.environ.get("MONGO_PWD")}@cluster0.ebiunpa.mongodb.net/?retryWrites=true&w=majority'
)
app = Flask(__name__)
db = client.test_database
lecturers = db.lecturers
tags = db.tags

@app.route("/")
def hello_world():
    return "<p>Hello TdA</p>"

@app.route("/api")
def api():
    return {"secret":"The cake is a lie"}

@app.route("/lecturer")
def lecturer():
    return render_template("lecturer.html")

@app.route("/api/lecturers", methods=["GET", "POST"])
def api_lecturers():
    if request.method == 'POST':
        new_lecturer_json = request.get_json()
        try:
            # Validate by creating lecturer object
            new_lecturer_json = NewLecturer(**new_lecturer_json).model_dump()

            new_lecturer_json["_id"] = str(uuid.uuid4())
            lecturers.insert_one(new_lecturer_json)

        except ValidationError as e:
            # Validation not successfull
            pass
    
    # Renaming keys "_id" to "uuid" 
    found_lecturers: List[Dict[str, Any]] = list(lecturers.find())
    for i in range(len(found_lecturers)):
        found_lecturers[i]['uuid'] = found_lecturers[i].pop('_id')

    return json.loads(json_util.dumps({"lecturers": found_lecturers}))

@app.route("/api/lecturers/<string:uuid>", methods=["GET"])
def get_specific_lecturer(uuid: str):
    found_lecturer = lecturers.find_one({"_id": uuid})
    found_lecturer["uuid"] = found_lecturer.pop("_id")

    if found_lecturer is None:
        return {"code": 404, "message": "User not found"}, 404
    else:
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
            lecturers.update_one({"_id": uuid}, {"$set": updated_lecturer_json})
            return get_specific_lecturer(uuid)
        
        except ValidationError as e:
            return {"code": 400, "message": "Invalid data"}, 400
        
    else:
        return {"code": 404, "message": "User not found"}, 404

if __name__ == '__main__':
    app.jinja_env.auto_reload = True
    app.config['TEMPLATES_AUTO_RELOAD'] = True
    app.run(debug=True, host='0.0.0.0')

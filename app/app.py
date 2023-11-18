import os
import json
from bson import json_util, ObjectId
from dotenv import load_dotenv
from flask import Flask, render_template, request
from pymongo.mongo_client import MongoClient


load_dotenv()
client = MongoClient(
    f'mongodb+srv://{os.environ.get("MONGO_USERNAME")}:{os.environ.get("MONGO_PWD")}@cluster0.ebiunpa.mongodb.net/?retryWrites=true&w=majority'
)
app = Flask(__name__)
db = client.test_database
lecturers = db.lecturers


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
        new_lecturer = request.get_json()
        print(new_lecturer)
        if new_lecturer:
            lecturers.insert_one(new_lecturer)
    return json.loads(json_util.dumps({"lecturers": list(lecturers.find())}))

@app.route("/api/delete/<string:id>", methods=["DELETE"])
def api_delete(id):
    deleted = bool(lecturers.delete_one({"_id": ObjectId(id)}).deleted_count)
    
    if deleted:
        return '', 204
    else:
        return {"code": 404, "message": "User not found"}

if __name__ == '__main__':
    app.jinja_env.auto_reload = True
    app.config['TEMPLATES_AUTO_RELOAD'] = True
    app.run(debug=True, host='0.0.0.0')

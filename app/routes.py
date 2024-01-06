from flask import render_template
from app import app, api


@app.route("/lecturer/<string:uuid>")
def lecturer(uuid: str):
    lecturer = api.get_specific_lecturer(uuid)
    if lecturer[1] == 404:
        return lecturer

    return render_template("lecturer.html", **lecturer[0])


@app.route("/")
def hello_world():
    return render_template("home.html")

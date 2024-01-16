from flask import render_template, redirect, url_for
from app import app, api


@app.route("/lecturer/<string:uuid>")
def lecturer(uuid: str):
    lecturer = api.get_specific_lecturer(uuid.strip())
    if lecturer[1] == 404:
        return lecturer

    return render_template("lecturer.html", **lecturer[0])

@app.route("/lecturer")
def lecturer_empty():
    return redirect('/')

@app.route("/")
def hello_world():
    return render_template("home.html", tags=api.get_all_tags()[0], locations=api.get_all_locations()[0])

from flask import render_template, redirect
from app import app, api, utils


@app.route("/lecturer/<string:uuid>")
def lecturer(uuid: str):
    lecturer = api.get_specific_lecturer(uuid.strip())
    if lecturer[1] == 404:
        return lecturer

    return render_template("lecturer.html", **lecturer[0])

@app.route("/lecturer")
def lecturer_empty():
    return redirect('/')

@app.route("/lecturer-zone")
def lecturer_zone():
    return render_template("lecturer_zone.html")

@app.route("/lecturer-zone-login")
def lecturer_zone_login():
    return render_template("lecturer_zone_login.html")

@app.route("/")
def hello_world():
    return render_template("home.html", tags=utils.get_all_tags(), locations=utils.get_all_locations(), max_price=utils.get_max_price())

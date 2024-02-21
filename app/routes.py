from flask import render_template, redirect, session
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

    if 'logged_in' not in session or not bool(session.get("logged_in")):
        return redirect("/lecturer-login")

    return render_template("lecturer_zone.html")

@app.route("/lecturer-login")
def lecturer_zone_login():
    return render_template("lecturer_zone_login.html")

@app.route("/lecturer-logout")
def logout_lecturer():
    session["logged_in"] = False
    return redirect('/lecturer-login')

@app.route("/")
def hello_world():
    return render_template("home.html", tags=utils.get_all_tags(), locations=utils.get_all_locations(), max_price=utils.get_max_price())

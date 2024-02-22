from flask import render_template, redirect, session, request
from app import app, api, utils, db

credentials = db.credentials

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
    if not bool(session.get("logged_in")):
        return redirect("/lecturer-login")

    return render_template("lecturer_zone.html")


@app.route("/lecturer-login", methods=["GET", "POST"])
def lecturer_login():

    if bool(session.get("logged_in")):
        return redirect("/lecturer-zone")

    if request.method == "GET":
        return render_template("lecturer_login.html")

    elif request.method == "POST":
        
        username: str|None = request.form.get("username")
        password: str|None = request.form.get("password")

        if username is None or password is None:
            return {"code": 401, "message": "Wrong username or password"}, 401
        
        username = username.strip()
        password = password.strip()
        hashed_password = utils.hash_password_bcrypt(password)

        if username == '' or hashed_password == '':
            return {"code": 401, "message": "Wrong username or password"}, 401

        lecturer_credentials = credentials.find_one({"username": {"$eq": username}, "hashed_password": {"$eq": hashed_password}})
        
        if not bool(lecturer_credentials):
            return {"code": 401, "message": "Wrong username or password"}, 401
        

        lecturer_uuid = lecturer_credentials.get("_id")
        session["logged_in"] = True
        session["lecturer_uuid"] = lecturer_uuid

        return redirect('/lecturer-zone')

    return {"code": 405, "message": "Method not allowed"}, 405


@app.route("/lecturer-logout")
def logout_lecturer():
    session.clear() # delete cookies
    return redirect('/lecturer-login')

@app.route("/")
def hello_world():
    return render_template("home.html", tags=utils.get_all_tags(), locations=utils.get_all_locations(), max_price=utils.get_max_price())

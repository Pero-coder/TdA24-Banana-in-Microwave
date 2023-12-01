from flask import render_template
from app import app

@app.route("/lecturer")
def lecturer():
    return render_template("lecturer.html")

@app.route("/")
def hello_world():
    return "<p>Hello TdA</p>"

from flask import Flask

app = Flask(__name__)

@app.route("/")
def hello_world():
    return "<p>Hello TdA</p>"

@app.route("/api")
def api():
    return {"secret":"The cake is a lie"}

import os
from dotenv import load_dotenv
from flask import Flask
from pymongo.mongo_client import MongoClient
from datetime import timedelta
import secrets


load_dotenv()
client = MongoClient(
    f'mongodb+srv://{os.environ.get("MONGO_USERNAME")}:{os.environ.get("MONGO_PWD")}@cluster0.ebiunpa.mongodb.net/?retryWrites=true&w=majority'
)
app = Flask(__name__)
app.secret_key = secrets.token_hex(16)  # Generate a random secret key
app.permanent_session_lifetime = timedelta(hours=4)  # Session expires after 4 hours
db = client.production_database

from app import routes, api, utils

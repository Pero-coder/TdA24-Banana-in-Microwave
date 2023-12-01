import os
from dotenv import load_dotenv
from flask import Flask
from pymongo.mongo_client import MongoClient


load_dotenv()
client = MongoClient(
    f'mongodb+srv://{os.environ.get("MONGO_USERNAME")}:{os.environ.get("MONGO_PWD")}@cluster0.ebiunpa.mongodb.net/?retryWrites=true&w=majority'
)
app = Flask(__name__)
db = client.test_database

from app import routes, api

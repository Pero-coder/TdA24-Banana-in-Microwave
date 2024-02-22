from app import db
from typing import List, Dict
import re
import bcrypt
import pymongo

lecturers = db.lecturers
tags = db.tags
credentials = db.credentials

def get_all_tags():
    existing_tags: List[Dict] = list()
    for tag in list(tags.find()):
        # Renaming keys "_id" to "uuid" 
        tag["uuid"] = str(tag.pop("_id"))
        existing_tags.append(tag)

    return existing_tags

def get_all_locations():
    existing_locations: List[str] = list()
    for lecturer in list(lecturers.find()):
        if lecturer["location"] not in existing_locations and lecturer["location"] is not None:
            existing_locations.append(lecturer["location"])

    return existing_locations

def get_max_price():
    max_price = 0
    for lecturer in list(lecturers.find()):
        if lecturer["price_per_hour"] is not None and lecturer["price_per_hour"] > max_price:
            max_price = lecturer["price_per_hour"]

    return max_price

def is_email_valid(email: str) -> bool:
    # source: https://stackabuse.com/python-validate-email-address-with-regular-expressions-regex/

    regex = re.compile(r'([A-Za-z0-9]+[.-_])*[A-Za-z0-9]+@[A-Za-z0-9-]+(\.[A-Z|a-z]{2,})+')
    return bool(re.fullmatch(regex, email))

def is_phone_number_valid(phone_number: str) -> bool:
    # works only without whitespaces
    clean_phone_number = phone_number.replace(' ', '')
    
    regex = re.compile(r'^(?:\+420|\+421)? ?\d{9}$')
    return bool(re.fullmatch(regex, clean_phone_number))


def hash_password_bcrypt(password: str) -> str:
    hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
    return hashed.decode('utf-8')

def check_hash_bcrypt(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))

def add_user_credentials_to_db(uuid: str, username: str, password: str) -> bool:
    hashed_password = hash_password_bcrypt(password)
    try:
        credentials.create_index("username", unique=True)
        credentials.insert_one({"_id": uuid, "username": username, "hashed_password": hashed_password})
        return True
    
    except pymongo.errors.DuplicateKeyError:
        print("Username already exists.")
        return False
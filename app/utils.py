from app import db
from typing import List, Dict
import re
import bcrypt
import pymongo
from bson import json_util
import json

lecturers = db.lecturers
tags = db.tags
credentials = db.credentials
reservations = db.reservations

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
    if email is None:
        return False

    # source: https://stackabuse.com/python-validate-email-address-with-regular-expressions-regex/

    regex = re.compile(r'([A-Za-z0-9]+[.-_])*[A-Za-z0-9]+@[A-Za-z0-9-]+(\.[A-Z|a-z]{2,})+')
    return bool(re.fullmatch(regex, email))

def is_phone_number_valid(phone_number: str) -> bool:
    if phone_number is None:
        return False

    # works only without whitespaces
    clean_phone_number = phone_number.replace(' ', '')
    
    regex = re.compile(r'^(?:\+420|\+421)? ?\d{9}$')
    return bool(re.fullmatch(regex, clean_phone_number))

def is_date_valid(date: str) -> bool:
    if date is None:
        return False
    
    # extremly simple regex (possible 29,30,31 in february)
    regex = re.compile(r'^\d{4}-(0[1-9]|1[0-2])-(0[1-9]|[12][0-9]|3[01])$')
    return bool(re.fullmatch(regex, date))

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
    
def change_user_password_in_db(uuid: str, new_password: str) -> bool:
    hashed_password = hash_password_bcrypt(new_password)
    try:
        result = credentials.update_one({"_id": uuid}, {"$set": {"hashed_password": hashed_password}})
        return result.modified_count > 0
    
    except pymongo.errors.PyMongoError as e:
        return False
    
def change_user_username_in_db(uuid: str, new_username: str) -> bool:
    try:
        username_exists = bool(credentials.find_one({"username": new_username}))

        if username_exists:
            return False

        result = credentials.update_one({"_id": uuid}, {"$set": {"username": new_username}})
        return result.modified_count > 0
    
    except pymongo.errors.PyMongoError as e:
        return False
    
def add_user_to_reservations_db(uuid: str) -> bool:
    try:
        reserved_hours = dict()
        reserved_hours["_id"] = uuid
        reserved_hours["teaching_dates"] = {}
        reservations.insert_one(reserved_hours)
        return True
    
    except Exception as e:
        print(e)
        return False

def delete_user_from_credentials_db(lecturer_uuid: str):
    result = credentials.delete_one({"_id": lecturer_uuid})
    return result.deleted_count > 0

def delete_user_from_reservations_db(lecturer_uuid: str):
    result = reservations.delete_one({"_id": lecturer_uuid})
    return result.deleted_count > 0

def delete_user_from_lecturers_db(lecturer_uuid: str):
    result = lecturers.delete_one({"_id": lecturer_uuid})
    return result.deleted_count > 0

def get_specific_lecturer(lecturer_uuid: str):
    lecturer_uuid = lecturer_uuid.strip()
    found_lecturer = lecturers.find_one({"_id": {"$eq": lecturer_uuid}})

    if found_lecturer is None:
        return {"code": 404, "message": "User not found"}, 404
    else:
        found_lecturer["uuid"] = found_lecturer.pop("_id")
        return json.loads(json_util.dumps(found_lecturer)), 200
from app import db
from typing import List, Dict


lecturers = db.lecturers
tags = db.tags


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

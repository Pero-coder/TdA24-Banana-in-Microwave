from pydantic import BaseModel, Field
from typing import Optional, List

class Tag(BaseModel):
    uuid: Optional[str] = None
    name: str


class Contact(BaseModel):
    telephone_numbers: List[str] = Field(..., min_items=1)
    emails: List[str] = Field(..., min_items=1)


class NewLecturer(BaseModel):
    title_before: Optional[str] = None
    first_name: str
    middle_name: Optional[str] = None
    last_name: str
    title_after: Optional[str] = None
    picture_url: Optional[str] = None
    location: Optional[str] = None
    claim: Optional[str] = None
    bio: Optional[str] = None
    tags: List[Tag] = Field(..., min_items=0, uniqueItems=True)
    price_per_hour: Optional[int] = Field(None, ge=0)
    contact: Contact

    username: str
    password: str

    class Config:
        extra = "ignore"


class EditLecturer(BaseModel):
    title_before: Optional[str] = None
    first_name: Optional[str] = None
    middle_name: Optional[str] = None
    last_name: Optional[str] = None
    title_after: Optional[str] = None
    picture_url: Optional[str] = None
    location: Optional[str] = None
    claim: Optional[str] = None
    bio: Optional[str] = None
    tags: Optional[List[Tag]] = Field(None, min_items=0, uniqueItems=True)
    price_per_hour: Optional[int] = Field(None, ge=0)
    contact: Optional[Contact] = None

    username: Optional[str] = None
    password: Optional[str] = None

    class Config:
        extra = "ignore"

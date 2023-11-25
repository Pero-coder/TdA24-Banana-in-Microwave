from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Literal

class Tag(BaseModel):
    uuid: Optional[str] = None
    name: str

class Lecturer(BaseModel):
    uuid: Optional[str] = None
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
    contact: Dict[Literal["telephone_numbers", "emails"], List[str]] = Field(..., min_items=1, uniqueItems=True)
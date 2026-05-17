from pydantic import BaseModel
from typing import Optional

# ---------------------------------------------------
# Schema for what LangChain AI extracts from Markdown
# ---------------------------------------------------
class EventExtracted(BaseModel):
    title: str
    organization: Optional[str] = None
    date: Optional[str] = None
    event_type: Optional[str] = None
    location: Optional[str] = None
    link: str
    quality_score: int = 5
    is_open: bool = True
    tags: Optional[str] = None

# ---------------------------------------------------
# Schema for creating an Event in the DB (internal)
# ---------------------------------------------------
class EventCreate(EventExtracted):
    source: Optional[str] = None

# ---------------------------------------------------
# Schema for returning an Event to the Frontend
# ---------------------------------------------------
class EventResponse(BaseModel):
    id: int
    title: str
    organization: Optional[str] = None
    date: Optional[str] = None
    event_type: Optional[str] = None
    location: Optional[str] = None
    link: str
    source: Optional[str] = None
    quality_score: int
    is_open: bool
    tags: Optional[str] = None


    class Config:
        from_attributes = True

# ---------------------------------------------------
# Schema for the manual event analyze endpoint
# ---------------------------------------------------
class EventText(BaseModel):
    raw_text: str

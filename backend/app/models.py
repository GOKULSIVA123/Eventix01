from sqlalchemy import Column, Integer, String, Boolean, UniqueConstraint
from .database import Base

class Event(Base):
    __tablename__ = "events"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    organization = Column(String, nullable=True)
    date = Column(String, nullable=True)
    event_type = Column(String, nullable=True)
    location = Column(String, nullable=True)
    quality_score = Column(Integer, default=5)      # 1-10 AI assigned score
    is_open = Column(Boolean, default=True)         # Is registration still open?
    tags = Column(String, nullable=True)            # Comma separated e.g. "React, AI"
    link = Column(String, unique=True, index=True, nullable=False)

    source = Column(String, nullable=True)



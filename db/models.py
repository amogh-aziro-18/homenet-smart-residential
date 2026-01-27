from sqlalchemy import Column, String, Integer, DateTime, Text
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()


class TaskDB(Base):
    __tablename__ = "tasks"

    task_id = Column(String, primary_key=True, index=True)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=False)

    asset_type = Column(String, nullable=False)
    asset_id = Column(String, nullable=False)
    building_id = Column(String, nullable=False)

    priority = Column(String, nullable=False)
    sla_hours = Column(Integer, nullable=False)

    status = Column(String, nullable=False)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)
    notes = Column(Text, nullable=True)

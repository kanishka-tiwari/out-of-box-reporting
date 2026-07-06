from sqlalchemy import Column, Integer, String, Float, DateTime
from app.database import Base
import datetime

class ExcelSource(Base):
    __tablename__ = "excel_sources"
    id = Column(Integer, primary_key=True, index=True)
    file_url = Column(String, unique=True, nullable=False)
    last_etag = Column(String, nullable=True)      # Tracks HTTP ETag headers
    last_modified = Column(String, nullable=True)  # Tracks last modification string

class Transaction(Base):
    __tablename__ = "transactions"
    id = Column(Integer, primary_key=True, index=True)
    transaction_id = Column(String, unique=True, index=True)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)
    employee_id = Column(String)
    amount = Column(Float)
    vendor = Column(String)
    category = Column(String)
    justification = Column(String)
    risk_score = Column(Integer, default=-1) # -1 means pending analysis
    ai_flags = Column(String, default="Pending AI Processing")
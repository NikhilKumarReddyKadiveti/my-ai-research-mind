from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
import datetime

Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True)
    email = Column(String(100), unique=True, index=True)
    hashed_password = Column(String(100))
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    
    research_history = relationship("ResearchHistory", back_populates="user")

class ResearchHistory(Base):
    __tablename__ = "research_history"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    query = Column(String(255))
    summary = Column(Text)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    
    user = relationship("User", back_populates="research_history")
    sources = relationship("Source", back_populates="research")

class Source(Base):
    __tablename__ = "sources"
    id = Column(Integer, primary_key=True, index=True)
    research_id = Column(Integer, ForeignKey("research_history.id"))
    title = Column(String(255))
    url = Column(String(500))
    content = Column(Text)
    
    research = relationship("ResearchHistory", back_populates="sources")

class SavedReport(Base):
    __tablename__ = "saved_reports"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    title = Column(String(255))
    content = Column(Text)
    format = Column(String(20)) # pdf, md, docx
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

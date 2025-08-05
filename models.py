"""
Database models for Wizzy Bot persistent storage
"""
from sqlalchemy import create_engine, Column, String, Text, DateTime, Integer, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import os

Base = declarative_base()

class ChatHistory(Base):
    """Store conversation messages for each chat session"""
    __tablename__ = 'chat_history'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String(50), nullable=False, index=True)
    message_type = Column(String(20), nullable=False)  # 'human' or 'ai'
    content = Column(Text, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)
    metadata = Column(JSON, default={})  # For additional message metadata

class DocumentContext(Base):
    """Store uploaded documents and their content"""
    __tablename__ = 'document_contexts'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String(50), nullable=False, index=True)
    filename = Column(String(255), nullable=False)
    content = Column(Text, nullable=False)
    summary = Column(Text)
    file_type = Column(String(20))
    file_size = Column(Integer)
    uploaded_at = Column(DateTime, default=datetime.utcnow)
    metadata = Column(JSON, default={})

class UserSession(Base):
    """Store user session information"""
    __tablename__ = 'user_sessions'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String(50), unique=True, nullable=False, index=True)
    user_name = Column(String(100))
    first_interaction = Column(DateTime, default=datetime.utcnow)
    last_interaction = Column(DateTime, default=datetime.utcnow)
    total_messages = Column(Integer, default=0)
    preferences = Column(JSON, default={})

# Database connection and session management
class DatabaseManager:
    def __init__(self, database_url: str):
        self.engine = create_engine(database_url)
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        
    def create_tables(self):
        """Create all tables if they don't exist"""
        Base.metadata.create_all(bind=self.engine)
        
    def get_session(self):
        """Get a database session"""
        return self.SessionLocal()
        
    def close_session(self, session):
        """Close a database session"""
        session.close()

# Initialize database manager
def get_database_manager():
    """Get database manager instance"""
    database_url = os.getenv('DATABASE_URL', 'sqlite:///wizzy_bot.db')
    
    # Handle Heroku DATABASE_URL format
    if database_url.startswith('postgres://'):
        database_url = database_url.replace('postgres://', 'postgresql://', 1)
    
    db_manager = DatabaseManager(database_url)
    db_manager.create_tables()
    return db_manager

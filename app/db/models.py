from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, Text
from sqlalchemy.orm import relationship
from datetime import datetime
from .base import Base


class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    is_active = Column(Boolean, default=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, index=True)
    
    # Relationships
    analyses = relationship("Analysis", back_populates="user", cascade="all, delete-orphan")
    chat_messages = relationship("ChatMessage", back_populates="user", cascade="all, delete-orphan")
    chat_sessions = relationship("ChatSession", back_populates="user", cascade="all, delete-orphan")  # NEW


class Analysis(Base):
    __tablename__ = "analyses"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True)
    url = Column(String, index=True)
    analysis_id = Column(String, unique=True, index=True)  # Visible ID: ANALYSIS-ABC12345
    status = Column(String, default="pending")  # pending, processing, completed, failed
    
    # SEO Results
    seo_overall_score = Column(Integer, nullable=True)
    seo_strengths = Column(Text, nullable=True)  # JSON string
    seo_weaknesses = Column(Text, nullable=True)  # JSON string
    seo_missing_elements = Column(Text, nullable=True)  # JSON string
    seo_recommendations = Column(Text, nullable=True)  # JSON string
    
    # UX Results
    ux_overall_score = Column(Integer, nullable=True)
    ux_strengths = Column(Text, nullable=True)  # JSON string
    ux_weaknesses = Column(Text, nullable=True)  # JSON string
    ux_missing_elements = Column(Text, nullable=True)  # JSON string
    ux_recommendations = Column(Text, nullable=True)  # JSON string
    
    error = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    completed_at = Column(DateTime, nullable=True)
    processing_time_ms = Column(Integer, nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="analyses")

class ChatSession(Base):
    __tablename__ = "chat_sessions"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True)
    analysis_id = Column(Integer, ForeignKey("analyses.id"), nullable=True, index=True)
    
    # Auto-generated title from first message
    title = Column(String(255), nullable=True)
    session_type = Column(String(50), default="universal")  # 'specific' or 'universal'
    
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, index=True)
    
    # Relationships
    user = relationship("User", back_populates="chat_sessions")
    analysis = relationship("Analysis")
    messages = relationship("ChatMessage", back_populates="session", cascade="all, delete-orphan")
class ChatMessage(Base):
    __tablename__ = "chat_messages"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True)
    session_id = Column(Integer, ForeignKey("chat_sessions.id"), index=True)  # NEW
    analysis_id = Column(Integer, ForeignKey("analyses.id"), nullable=True, index=True)
    
    user_message = Column(Text, nullable=False)
    assistant_response = Column(Text, nullable=False)
    source_analyses = Column(Text, nullable=True)
    relevance_scores = Column(Text, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    
    # Relationships
    user = relationship("User", back_populates="chat_messages")
    session = relationship("ChatSession", back_populates="messages")  # NEW
    analysis = relationship("Analysis")
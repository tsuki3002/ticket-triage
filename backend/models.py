from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import relationship

from database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    email = Column(String(150), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    role = Column(String(50), default="agent")
    is_active = Column(Boolean, default=True)

    assigned_tickets = relationship("Ticket", back_populates="assigned_user")
    comments = relationship("Comment", back_populates="author")
    activities = relationship("Activity", back_populates="user")


class Team(Base):
    __tablename__ = "teams"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False)

    assigned_tickets = relationship("Ticket", back_populates="assigned_team")


class Ticket(Base):
    __tablename__ = "tickets"

    id = Column(Integer, primary_key=True, index=True)

    # Original customer-submitted fields — description is never modified by AI
    customer_name = Column(String(100), nullable=False)
    customer_email = Column(String(150), nullable=False)
    subject = Column(String(200), nullable=False)
    description = Column(Text, nullable=False)
    product_module = Column(String(100), nullable=True)
    attachment_link = Column(String(500), nullable=True)

    # Current confirmed values (AI-suggested, human-editable)
    summary = Column(String(500), nullable=True)
    category = Column(String(50), nullable=True)
    priority = Column(String(20), nullable=True)
    priority_reason = Column(String(300), nullable=True)
    recommended_team = Column(String(100), nullable=True)
    suggested_response = Column(String(1000), nullable=True)

    # Assignment
    assigned_team_id = Column(Integer, ForeignKey("teams.id"), nullable=True)
    assigned_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    status = Column(String(30), nullable=False, default="Open")

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    assigned_team = relationship("Team", back_populates="assigned_tickets")
    assigned_user = relationship("User", back_populates="assigned_tickets")
    ai_suggestions = relationship("AISuggestion", back_populates="ticket", cascade="all, delete-orphan")
    comments = relationship("Comment", back_populates="ticket", cascade="all, delete-orphan")
    activities = relationship("Activity", back_populates="ticket", cascade="all, delete-orphan")


class AISuggestion(Base):
    """
    Immutable record of what the AI actually returned. Kept separate from
    Ticket's live fields so AI output always stays distinguishable from
    human-confirmed values, even after edits.
    """
    __tablename__ = "ai_suggestions"

    id = Column(Integer, primary_key=True, index=True)
    ticket_id = Column(Integer, ForeignKey("tickets.id"), nullable=False)

    summary = Column(String(500), nullable=False)
    category = Column(String(50), nullable=False)
    priority = Column(String(20), nullable=False)
    priority_reason = Column(String(300), nullable=False)
    recommended_team = Column(String(100), nullable=False)
    suggested_response = Column(String(1000), nullable=False)
    raw_response = Column(Text, nullable=True)  # full raw JSON, for debugging

    created_at = Column(DateTime, default=datetime.utcnow)

    ticket = relationship("Ticket", back_populates="ai_suggestions")


class Comment(Base):
    __tablename__ = "comments"

    id = Column(Integer, primary_key=True, index=True)
    ticket_id = Column(Integer, ForeignKey("tickets.id"), nullable=False)
    author_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    text = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    ticket = relationship("Ticket", back_populates="comments")
    author = relationship("User", back_populates="comments")


class Activity(Base):
    __tablename__ = "activities"

    id = Column(Integer, primary_key=True, index=True)
    ticket_id = Column(Integer, ForeignKey("tickets.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    activity_type = Column(String(50), nullable=False)  # e.g. "ticket_created", "status_changed"
    description = Column(String(500), nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)

    ticket = relationship("Ticket", back_populates="activities")
    user = relationship("User", back_populates="activities")
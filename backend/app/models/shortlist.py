from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base


class Shortlist(Base):
    __tablename__ = "shortlists"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    guest_session_id = Column(String(64), ForeignKey("guest_sessions.id"), nullable=True)
    name = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="shortlists")
    candidates = relationship("ShortlistCandidate", back_populates="shortlist", cascade="all, delete-orphan")


class ShortlistCandidate(Base):
    __tablename__ = "shortlist_candidates"

    shortlist_id = Column(Integer, ForeignKey("shortlists.id"), primary_key=True)
    candidate_id = Column(Integer, ForeignKey("candidates.id"), primary_key=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    shortlist = relationship("Shortlist", back_populates="candidates")
    candidate = relationship("Candidate")

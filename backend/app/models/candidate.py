from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base


class Candidate(Base):
    __tablename__ = "candidates"

    id = Column(Integer, primary_key=True, index=True)

    github_id = Column(Integer, unique=True, nullable=False, index=True)
    github_username = Column(String(255), unique=True, nullable=False, index=True)

    name = Column(String(255), nullable=True)
    avatar_url = Column(Text, nullable=True)
    profile_url = Column(Text, nullable=True)
    bio = Column(Text, nullable=True)
    company = Column(String(255), nullable=True)
    location = Column(String(255), nullable=True)

    followers = Column(Integer, default=0)
    following = Column(Integer, default=0)
    public_repos = Column(Integer, default=0)

    profile_completeness = Column(String(50), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    last_synced_at = Column(DateTime(timezone=True), server_default=func.now())

    repositories = relationship(
        "CandidateRepository",
        back_populates="candidate",
        cascade="all, delete-orphan",
    )

    languages = relationship(
        "CandidateLanguage",
        back_populates="candidate",
        cascade="all, delete-orphan",
    )


class CandidateRepository(Base):
    __tablename__ = "candidate_repositories"

    id = Column(Integer, primary_key=True, index=True)

    candidate_id = Column(Integer, ForeignKey("candidates.id"), nullable=False)
    github_repo_id = Column(Integer, unique=True, nullable=False, index=True)

    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    url = Column(Text, nullable=True)
    language = Column(String(100), nullable=True)

    stars = Column(Integer, default=0)
    forks = Column(Integer, default=0)
    pushed_at = Column(String(100), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    last_synced_at = Column(DateTime(timezone=True), server_default=func.now())

    candidate = relationship(
        "Candidate",
        back_populates="repositories",
    )


class CandidateLanguage(Base):
    __tablename__ = "candidate_languages"

    id = Column(Integer, primary_key=True, index=True)

    candidate_id = Column(Integer, ForeignKey("candidates.id"), nullable=False)
    language = Column(String(100), nullable=False)
    repo_count = Column(Integer, default=0)

    candidate = relationship(
        "Candidate",
        back_populates="languages",
    )

    __table_args__ = (
        UniqueConstraint("candidate_id", "language", name="uq_candidate_language"),
    )
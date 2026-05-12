from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base


class EvaluationRun(Base):
    __tablename__ = "evaluation_runs"

    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(Integer, ForeignKey("jobs.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    guest_session_id = Column(String(64), ForeignKey("guest_sessions.id"), nullable=True)

    # pending | running | completed | failed
    status = Column(String(50), nullable=False, default="pending")
    candidate_count = Column(Integer, default=0)
    completed_count = Column(Integer, default=0)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)

    job = relationship("Job", back_populates="evaluation_runs")
    candidate_evaluations = relationship(
        "CandidateEvaluation",
        back_populates="evaluation_run",
        cascade="all, delete-orphan",
    )


class CandidateEvaluation(Base):
    __tablename__ = "candidate_evaluations"

    id = Column(Integer, primary_key=True, index=True)
    evaluation_run_id = Column(Integer, ForeignKey("evaluation_runs.id"), nullable=False, index=True)
    candidate_id = Column(Integer, ForeignKey("candidates.id"), nullable=False, index=True)

    heuristic_score = Column(Float, nullable=True)
    ai_score = Column(Float, nullable=True)
    final_score = Column(Float, nullable=True)

    summary = Column(Text, nullable=True)
    strengths_json = Column(Text, nullable=True)
    concerns_json = Column(Text, nullable=True)
    evidence_json = Column(Text, nullable=True)

    # Sub-scores stored as 0–100 floats
    technical_match = Column(Float, nullable=True)
    activity_signal = Column(Float, nullable=True)
    profile_completeness_score = Column(Float, nullable=True)

    # pending | completed | failed
    status = Column(String(50), nullable=False, default="pending")

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    evaluation_run = relationship("EvaluationRun", back_populates="candidate_evaluations")
    candidate = relationship("Candidate")

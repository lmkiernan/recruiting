from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.schemas.candidate import CandidateSummary


class EvaluationRunCreate(BaseModel):
    job_id: int


class EvaluationRunOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    job_id: int
    status: str
    candidate_count: int
    completed_count: int
    created_at: datetime
    completed_at: datetime | None


class ScoreBreakdownItem(BaseModel):
    label: str
    score: float
    max: int


class CandidateEvaluationOut(BaseModel):
    id: int
    candidate_id: int
    heuristic_score: float | None
    ai_score: float | None
    final_score: float | None
    technical_match: float | None
    activity_signal: float | None
    profile_completeness_score: float | None
    summary: str | None
    breakdown: list[ScoreBreakdownItem]
    evidence: list[str]
    concerns: list[str]
    status: str
    candidate: CandidateSummary


class EvaluationRunWithResults(EvaluationRunOut):
    evaluations: list[CandidateEvaluationOut]

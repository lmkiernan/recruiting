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


class CandidateEvaluationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    candidate_id: int
    heuristic_score: float | None
    final_score: float | None
    technical_match: float | None
    activity_signal: float | None
    profile_completeness_score: float | None
    status: str
    candidate: CandidateSummary


class EvaluationRunWithResults(EvaluationRunOut):
    evaluations: list[CandidateEvaluationOut]

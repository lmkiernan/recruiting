import json
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, selectinload

from app.core.deps import get_db
from app.models.candidate import Candidate
from app.models.evaluation import CandidateEvaluation, EvaluationRun
from app.models.job import Job
from app.schemas.candidate import CandidateLanguage, CandidateSummary
from app.schemas.evaluation import CandidateEvaluationOut, EvaluationRunOut, EvaluationRunWithResults, EvaluationRunCreate
from app.services.candidate_signal_service import score_all_candidates

router = APIRouter(prefix="/evaluation-runs", tags=["evaluations"])


def _candidate_to_summary(candidate) -> CandidateSummary:
    top_languages = sorted(candidate.languages, key=lambda l: l.repo_count, reverse=True)[:5]
    return CandidateSummary(
        id=candidate.id,
        github_username=candidate.github_username,
        name=candidate.name,
        avatar_url=candidate.avatar_url,
        profile_url=candidate.profile_url,
        bio=candidate.bio,
        location=candidate.location,
        company=candidate.company,
        followers=candidate.followers,
        public_repos=candidate.public_repos,
        profile_completeness=candidate.profile_completeness,
        top_languages=[CandidateLanguage(language=l.language, repo_count=l.repo_count) for l in top_languages],
    )


@router.post("", response_model=EvaluationRunWithResults, status_code=201)
def create_evaluation_run(body: EvaluationRunCreate, db: Session = Depends(get_db)) -> EvaluationRunWithResults:
    job = db.query(Job).filter(Job.id == body.job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    run = EvaluationRun(job_id=job.id, status="running")
    db.add(run)
    db.flush()

    scored = score_all_candidates(db, job.description)

    evaluations: list[CandidateEvaluation] = []
    for result in scored:
        candidate = result["candidate"]
        ev = CandidateEvaluation(
            evaluation_run_id=run.id,
            candidate_id=candidate.id,
            heuristic_score=result["heuristic_score"],
            final_score=result["final_score"],
            technical_match=result["technical_match"],
            activity_signal=result["activity_signal"],
            profile_completeness_score=result["profile_completeness_score"],
            evidence_json=json.dumps(result["evidence"]),
            status="completed",
        )
        db.add(ev)
        evaluations.append((ev, candidate))

    run.status = "completed"
    run.candidate_count = len(scored)
    run.completed_count = len(scored)
    run.completed_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(run)

    eval_outs = [
        CandidateEvaluationOut(
            id=ev.id,
            candidate_id=ev.candidate_id,
            heuristic_score=ev.heuristic_score,
            final_score=ev.final_score,
            technical_match=ev.technical_match,
            activity_signal=ev.activity_signal,
            profile_completeness_score=ev.profile_completeness_score,
            status=ev.status,
            candidate=_candidate_to_summary(candidate),
        )
        for ev, candidate in evaluations
    ]

    return EvaluationRunWithResults(
        id=run.id,
        job_id=run.job_id,
        status=run.status,
        candidate_count=run.candidate_count,
        completed_count=run.completed_count,
        created_at=run.created_at,
        completed_at=run.completed_at,
        evaluations=eval_outs,
    )


@router.get("/{run_id}", response_model=EvaluationRunOut)
def get_evaluation_run(run_id: int, db: Session = Depends(get_db)) -> EvaluationRunOut:
    run = db.query(EvaluationRun).filter(EvaluationRun.id == run_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Evaluation run not found")
    return run


@router.get("/{run_id}/candidates", response_model=list[CandidateEvaluationOut])
def get_run_candidates(run_id: int, db: Session = Depends(get_db)) -> list[CandidateEvaluationOut]:
    run = db.query(EvaluationRun).filter(EvaluationRun.id == run_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Evaluation run not found")

    rows = (
        db.query(CandidateEvaluation)
        .options(
            selectinload(CandidateEvaluation.candidate).selectinload(Candidate.languages)
        )
        .filter(CandidateEvaluation.evaluation_run_id == run_id)
        .order_by(CandidateEvaluation.final_score.desc())
        .all()
    )

    return [
        CandidateEvaluationOut(
            id=ev.id,
            candidate_id=ev.candidate_id,
            heuristic_score=ev.heuristic_score,
            final_score=ev.final_score,
            technical_match=ev.technical_match,
            activity_signal=ev.activity_signal,
            profile_completeness_score=ev.profile_completeness_score,
            status=ev.status,
            candidate=_candidate_to_summary(ev.candidate),
        )
        for ev in rows
    ]

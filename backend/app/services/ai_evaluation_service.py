"""
AI candidate evaluation using OpenAI.

Runs as a FastAPI background task after heuristic scoring completes.
Evaluates the top N candidates by heuristic score in batches of 5,
persisting results incrementally so the frontend sees live updates.

Score blending:  final_score = ai_score * 0.7 + heuristic_score * 0.3
"""

import json
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone

from openai import OpenAI
from sqlalchemy.orm import Session, selectinload

from app.core.config import settings
from app.core.database import SessionLocal
from app.models.candidate import Candidate
from app.models.evaluation import CandidateEvaluation, EvaluationRun

logger = logging.getLogger(__name__)

AI_TOP_N = 25
AI_BATCH_SIZE = 5
MODEL = "gpt-4o-mini"

SYSTEM_PROMPT = """You are an expert technical recruiter evaluating GitHub developer profiles.
Be specific, evidence-based, and focus only on what is observable from the public profile data provided.
Do not invent information that is not present in the candidate profiles."""


# ---------------------------------------------------------------------------
# Candidate profile serialiser — keeps prompts concise
# ---------------------------------------------------------------------------

def _profile_for_prompt(candidate: Candidate) -> dict:
    langs = sorted(candidate.languages, key=lambda l: l.repo_count, reverse=True)
    repos = sorted(candidate.repositories, key=lambda r: r.stars, reverse=True)
    return {
        "id": candidate.id,
        "username": candidate.github_username,
        "name": candidate.name,
        "bio": candidate.bio,
        "company": candidate.company,
        "location": candidate.location,
        "followers": candidate.followers,
        "public_repos": candidate.public_repos,
        "profile_completeness": candidate.profile_completeness,
        "top_languages": [
            {"language": l.language, "repos": l.repo_count}
            for l in langs[:8]
        ],
        "top_repos": [
            {
                "name": r.name,
                "description": r.description,
                "language": r.language,
                "stars": r.stars,
                "pushed_at": r.pushed_at,
            }
            for r in repos[:8]
        ],
    }


# ---------------------------------------------------------------------------
# OpenAI batch call
# ---------------------------------------------------------------------------

def _evaluate_batch(client: OpenAI, jd: str, profiles: list[dict]) -> list[dict]:
    user_prompt = f"""Evaluate these candidates against the job description below.

Return a JSON object with an "evaluations" array — one object per candidate.

Each evaluation object must include:
- "candidate_id": integer (the candidate's id field)
- "ai_score": integer 0-100 (role-specific fit; be honest and spread scores out)
- "summary": string (2-3 sentences, specific to this role, evidence-backed)
- "strengths": array of 2-4 strings (specific strengths relevant to the JD)
- "concerns": array of 1-3 strings (honest gaps for this specific role)
- "evidence": array of 2-4 strings (direct observations from the profile)

Job Description:
{jd}

Candidates:
{json.dumps(profiles, indent=2)}"""

    response = client.chat.completions.create(
        model=MODEL,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.3,
        timeout=60,
    )

    raw = response.choices[0].message.content or "{}"
    data = json.loads(raw)
    return data.get("evaluations", [])


# ---------------------------------------------------------------------------
# Score blending
# ---------------------------------------------------------------------------

def _blend(heuristic: float | None, ai: float | None) -> float:
    if heuristic is None and ai is None:
        return 0.0
    if ai is None:
        return heuristic or 0.0
    if heuristic is None:
        return float(ai)
    return round(float(ai) * 0.7 + float(heuristic) * 0.3, 1)


# ---------------------------------------------------------------------------
# Background task entry point
# ---------------------------------------------------------------------------

def run_ai_evaluation(run_id: int, job_description: str) -> None:
    """
    Called as a FastAPI background task. Opens its own DB session.
    Selects the top AI_TOP_N candidates by heuristic score,
    evaluates them in batches, and persists results incrementally.
    """
    if not settings.OPENAI_API_KEY:
        logger.warning("OPENAI_API_KEY not set — skipping AI evaluation for run %d", run_id)
        db = SessionLocal()
        try:
            _mark_run_db(db, run_id, "completed")
        finally:
            db.close()
        return

    client = OpenAI(api_key=settings.OPENAI_API_KEY)
    db = SessionLocal()

    try:
        # Select top N evaluations to AI-score
        top_evals = (
            db.query(CandidateEvaluation)
            .filter_by(evaluation_run_id=run_id)
            .order_by(CandidateEvaluation.heuristic_score.desc())
            .limit(AI_TOP_N)
            .all()
        )

        if not top_evals:
            _mark_run_db(db, run_id, "completed")
            return

        candidate_ids = [ev.candidate_id for ev in top_evals]

        # Preload candidate data once (repos + languages for prompt)
        candidates_by_id: dict[int, Candidate] = {
            c.id: c
            for c in db.query(Candidate)
            .options(
                selectinload(Candidate.languages),
                selectinload(Candidate.repositories),
            )
            .filter(Candidate.id.in_(candidate_ids))
            .all()
        }

        run = db.query(EvaluationRun).filter_by(id=run_id).first()
        if not run:
            return

        # Build all batch inputs from already-loaded in-memory data
        batches: list[tuple[list[CandidateEvaluation], list[dict]]] = [
            (
                top_evals[i : i + AI_BATCH_SIZE],
                [
                    _profile_for_prompt(candidates_by_id[ev.candidate_id])
                    for ev in top_evals[i : i + AI_BATCH_SIZE]
                    if ev.candidate_id in candidates_by_id
                ],
            )
            for i in range(0, len(top_evals), AI_BATCH_SIZE)
        ]

        def call_batch(idx: int, batch_evals: list, profiles: list[dict]) -> tuple[int, list, list[dict]]:
            try:
                return idx, batch_evals, _evaluate_batch(client, job_description, profiles)
            except Exception as exc:
                logger.error("AI batch %d failed for run %d: %s", idx, run_id, exc)
                return idx, batch_evals, []

        # Fire all batches in parallel — each is an independent HTTP call to OpenAI
        with ThreadPoolExecutor(max_workers=len(batches)) as pool:
            futures = {
                pool.submit(call_batch, i, batch_evals, profiles): i
                for i, (batch_evals, profiles) in enumerate(batches)
            }
            batch_results = [f.result() for f in as_completed(futures)]

        # Apply all results to the ORM objects (single session, no threads here)
        total_completed = 0
        for _, batch_evals, ai_results in batch_results:
            ai_by_id = {r["candidate_id"]: r for r in ai_results if "candidate_id" in r}
            for ev in batch_evals:
                result = ai_by_id.get(ev.candidate_id)
                if not result:
                    continue
                ai_score = result.get("ai_score")
                ev.ai_score = ai_score
                ev.final_score = _blend(ev.heuristic_score, ai_score)
                ev.summary = result.get("summary") or ev.summary
                ev.strengths_json = json.dumps(result.get("strengths") or [])
                ev.concerns_json = json.dumps(result.get("concerns") or [])
                ev.status = "completed"
                total_completed += 1

        run.completed_count = total_completed
        db.commit()
        logger.info("AI run %d: all %d batches done, %d scored", run_id, len(batches), total_completed)

        _mark_run_db(db, run_id, "completed")

    except Exception as exc:
        logger.exception("AI evaluation failed for run %d: %s", run_id, exc)
        try:
            _mark_run_db(db, run_id, "ai_failed")
        except Exception:
            pass
    finally:
        db.close()


def _mark_run_db(db: Session, run_id: int, status: str) -> None:
    run = db.query(EvaluationRun).filter_by(id=run_id).first()
    if run:
        run.status = status
        if status in ("completed", "ai_failed"):
            run.completed_at = datetime.now(timezone.utc)
        db.commit()



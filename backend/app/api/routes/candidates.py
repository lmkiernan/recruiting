from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session, selectinload

from app.core.deps import get_db
from app.models.candidate import Candidate, CandidateLanguage
from app.schemas.candidate import CandidateDetail, CandidateSummary

router = APIRouter(prefix="/candidates", tags=["candidates"])


def _build_summary(candidate: Candidate) -> CandidateSummary:
    top_languages = sorted(candidate.languages, key=lambda l: l.repo_count, reverse=True)[:5]
    return CandidateSummary(
        **{
            col: getattr(candidate, col)
            for col in [
                "id", "github_username", "name", "avatar_url", "profile_url",
                "bio", "location", "company", "followers", "public_repos",
                "profile_completeness",
            ]
        },
        top_languages=top_languages,
    )


@router.get("", response_model=list[CandidateSummary])
def list_candidates(
    q: str | None = Query(None, description="Text search on name, username, bio, location"),
    language: str | None = Query(None, description="Filter by primary language"),
    location: str | None = Query(None, description="Filter by location (partial match)"),
    min_followers: int | None = Query(None, ge=0),
    max_followers: int | None = Query(None, le=1999),
    min_repos: int | None = Query(None, ge=0),
    profile_completeness: str | None = Query(None, pattern="^(low|medium|high)$"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
) -> list[CandidateSummary]:
    query = db.query(Candidate).options(selectinload(Candidate.languages))

    if q:
        term = f"%{q}%"
        query = query.filter(
            Candidate.name.ilike(term)
            | Candidate.github_username.ilike(term)
            | Candidate.bio.ilike(term)
            | Candidate.location.ilike(term)
        )

    if language:
        query = query.join(Candidate.languages).filter(
            func.lower(CandidateLanguage.language) == language.lower()
        )

    if location:
        query = query.filter(Candidate.location.ilike(f"%{location}%"))

    if min_followers is not None:
        query = query.filter(Candidate.followers >= min_followers)

    if max_followers is not None:
        query = query.filter(Candidate.followers <= max_followers)

    if min_repos is not None:
        query = query.filter(Candidate.public_repos >= min_repos)

    if profile_completeness:
        query = query.filter(Candidate.profile_completeness == profile_completeness)

    candidates = (
        query.order_by(Candidate.followers.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )

    return [_build_summary(c) for c in candidates]


@router.get("/{candidate_id}", response_model=CandidateDetail)
def get_candidate(candidate_id: int, db: Session = Depends(get_db)) -> CandidateDetail:
    candidate = (
        db.query(Candidate)
        .options(
            selectinload(Candidate.repositories),
            selectinload(Candidate.languages),
        )
        .filter(Candidate.id == candidate_id)
        .first()
    )

    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")

    return CandidateDetail(
        **{
            col: getattr(candidate, col)
            for col in [
                "id", "github_username", "name", "avatar_url", "profile_url",
                "bio", "location", "company", "followers", "following",
                "public_repos", "profile_completeness", "created_at",
            ]
        },
        repositories=candidate.repositories,
        languages=candidate.languages,
        top_languages=sorted(candidate.languages, key=lambda l: l.repo_count, reverse=True)[:5],
    )

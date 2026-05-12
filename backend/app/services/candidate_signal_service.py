"""
Heuristic candidate scoring against a job description.

Produces a 0–100 score built from four components:
  technical_match   (40 pts) — language + keyword overlap with JD
  activity_signal   (30 pts) — recency of repo pushes
  follower_signal   (20 pts) — followers as a weak proxy for community standing
  completeness      (10 pts) — how filled-in the profile is

All sub-scores are also stored normalised to 0–100 for display.
"""

import math
import re
from datetime import datetime, timezone

from sqlalchemy.orm import Session, selectinload

from app.models.candidate import Candidate, CandidateLanguage, CandidateRepository

# ---------------------------------------------------------------------------
# Language / keyword dictionaries
# ---------------------------------------------------------------------------

# Maps lowercase text → canonical GitHub language name
LANGUAGE_MAP: dict[str, str] = {
    "python": "Python",
    "javascript": "JavaScript",
    "js": "JavaScript",
    "typescript": "TypeScript",
    "ts": "TypeScript",
    "go": "Go",
    "golang": "Go",
    "java": "Java",
    "ruby": "Ruby",
    "rust": "Rust",
    "c++": "C++",
    "cpp": "C++",
    "c#": "C#",
    "csharp": "C#",
    "php": "PHP",
    "swift": "Swift",
    "kotlin": "Kotlin",
    "scala": "Scala",
    "r": "R",
    "shell": "Shell",
    "bash": "Shell",
    "html": "HTML",
    "css": "CSS",
    "sql": "SQL",
    "dart": "Dart",
    "elixir": "Elixir",
    "haskell": "Haskell",
    "clojure": "Clojure",
    "ocaml": "OCaml",
    "lua": "Lua",
    "vim script": "Vim Script",
}

TECH_KEYWORDS: set[str] = {
    # Architecture / patterns
    "api", "rest", "restful", "graphql", "grpc", "microservices", "distributed",
    "event-driven", "serverless", "monolith",
    # Frontend
    "frontend", "react", "vue", "angular", "svelte", "nextjs", "next.js",
    "html", "css", "tailwind", "webpack", "vite",
    # Backend
    "backend", "server", "fastapi", "django", "flask", "express", "node",
    "nodejs", "spring", "rails", "laravel", "gin", "fiber", "actix",
    # Data
    "sql", "nosql", "postgresql", "postgres", "mysql", "sqlite", "mongodb",
    "redis", "elasticsearch", "kafka", "rabbitmq", "celery",
    # Cloud / infra
    "aws", "gcp", "azure", "cloud", "docker", "kubernetes", "k8s",
    "terraform", "ci/cd", "github actions", "linux",
    # Full-stack
    "full-stack", "fullstack",
    # ML / data science
    "machine learning", "ml", "deep learning", "nlp", "llm", "ai",
    "data science", "pytorch", "tensorflow", "scikit",
    # Practices
    "testing", "unit test", "integration test", "tdd", "agile", "startup",
    "open source", "scalable", "performance", "security",
    # Seniority (not scored, but captured for evidence)
    "junior", "senior", "lead", "principal", "staff",
}


# ---------------------------------------------------------------------------
# Parsing helpers
# ---------------------------------------------------------------------------

def _normalise(text: str) -> str:
    return text.lower()


def extract_languages(jd: str) -> list[str]:
    """Return canonical language names found in the job description."""
    norm = _normalise(jd)
    found: list[str] = []
    seen: set[str] = set()
    for keyword, canonical in LANGUAGE_MAP.items():
        # word-boundary match so "r" doesn't match "react"
        if re.search(rf"\b{re.escape(keyword)}\b", norm) and canonical not in seen:
            found.append(canonical)
            seen.add(canonical)
    return found


def extract_keywords(jd: str) -> list[str]:
    """Return tech keywords found in the job description."""
    norm = _normalise(jd)
    return [kw for kw in TECH_KEYWORDS if kw in norm]


# ---------------------------------------------------------------------------
# Sub-score calculations
# ---------------------------------------------------------------------------

def _language_score(
    candidate_languages: list[CandidateLanguage],
    jd_languages: list[str],
) -> float:
    """0–100. Each matched language scores proportionally to its repo_count weight."""
    if not jd_languages or not candidate_languages:
        return 0.0

    lang_map = {l.language.lower(): l.repo_count for l in candidate_languages}
    total_repos = sum(lang_map.values()) or 1
    matched_repos = sum(
        lang_map.get(jd_lang.lower(), 0) for jd_lang in jd_languages
    )
    return min(100.0, (matched_repos / total_repos) * 100)


def _keyword_score(
    candidate: Candidate,
    repos: list[CandidateRepository],
    jd_keywords: list[str],
) -> float:
    """0–100. Count distinct keyword hits across bio and repo descriptions."""
    if not jd_keywords:
        return 0.0

    corpus = " ".join(
        filter(None, [
            candidate.bio or "",
            candidate.company or "",
            *[repo.description or "" for repo in repos],
            *[repo.name or "" for repo in repos],
        ])
    ).lower()

    hits = sum(1 for kw in jd_keywords if kw in corpus)
    return min(100.0, (hits / max(len(jd_keywords), 1)) * 100)


def _activity_score(repos: list[CandidateRepository]) -> float:
    """0–100. Based on how recently repos were pushed to."""
    if not repos:
        return 0.0

    now = datetime.now(timezone.utc)
    scores: list[float] = []

    for repo in repos:
        if not repo.pushed_at:
            continue
        try:
            pushed = datetime.fromisoformat(repo.pushed_at.replace("Z", "+00:00"))
        except ValueError:
            continue
        days_ago = (now - pushed).days
        # Decay: pushed today = 100, 1 year ago ≈ 37, 3 years ago ≈ 5
        score = 100.0 * math.exp(-days_ago / 365)
        scores.append(score)

    return max(scores) if scores else 0.0


def _follower_score(followers: int) -> float:
    """0–100. Log-scaled within the expected 20–2000 range."""
    if followers <= 0:
        return 0.0
    # log(20) ≈ 3.0, log(2000) ≈ 7.6
    lo, hi = math.log(20), math.log(2000)
    clamped = min(max(math.log(followers + 1), lo), hi)
    return (clamped - lo) / (hi - lo) * 100


def _completeness_score(profile_completeness: str | None) -> float:
    return {"high": 100.0, "medium": 60.0, "low": 20.0}.get(profile_completeness or "", 0.0)


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

WEIGHTS = {
    "language": 0.40,
    "keyword": 0.30,
    "activity": 0.20,
    "follower": 0.05,
    "completeness": 0.05,
}


def score_candidate(
    candidate: Candidate,
    jd_languages: list[str],
    jd_keywords: list[str],
) -> dict:
    """
    Return a dict with heuristic_score and all sub-scores (each 0–100).
    """
    repos = candidate.repositories
    lang_score = _language_score(candidate.languages, jd_languages)
    kw_score = _keyword_score(candidate, repos, jd_keywords)
    act_score = _activity_score(repos)
    fol_score = _follower_score(candidate.followers or 0)
    comp_score = _completeness_score(candidate.profile_completeness)

    technical_match = lang_score * 0.57 + kw_score * 0.43  # blended technical signal
    activity_signal = act_score
    completeness = comp_score

    heuristic = (
        lang_score * WEIGHTS["language"]
        + kw_score * WEIGHTS["keyword"]
        + act_score * WEIGHTS["activity"]
        + fol_score * WEIGHTS["follower"]
        + comp_score * WEIGHTS["completeness"]
    )

    matched_languages = [
        lang for lang in jd_languages
        if any(l.language.lower() == lang.lower() for l in candidate.languages)
    ]

    return {
        "heuristic_score": round(heuristic, 1),
        "final_score": round(heuristic, 1),
        "technical_match": round(technical_match, 1),
        "activity_signal": round(activity_signal, 1),
        "profile_completeness_score": round(completeness, 1),
        "evidence": {
            "matched_languages": matched_languages,
            "top_languages": [l.language for l in candidate.languages[:5]],
            "repo_count": len(repos),
        },
    }


def score_all_candidates(db: Session, job_description: str) -> list[dict]:
    """
    Score every candidate in the database against the job description.
    Returns a list of dicts sorted by heuristic_score descending.
    """
    jd_languages = extract_languages(job_description)
    jd_keywords = extract_keywords(job_description)

    candidates = (
        db.query(Candidate)
        .options(selectinload(Candidate.languages), selectinload(Candidate.repositories))
        .all()
    )

    results = []
    for candidate in candidates:
        scores = score_candidate(candidate, jd_languages, jd_keywords)
        results.append({"candidate": candidate, **scores})

    results.sort(key=lambda r: r["heuristic_score"], reverse=True)
    return results

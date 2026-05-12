"""
Heuristic candidate scoring against a job description.

Score breakdown (sums to 100):
  Technical match  — 50 pts  (language overlap 30 + keyword overlap 20)
  Activity signal  — 25 pts  (recency of repo pushes)
  Profile signal   — 15 pts  (completeness 10 + followers 5)
  Repo quality     — 10 pts  (descriptions, stars)

Each component is computed on a 0–100 sub-scale, then weighted.
"""

import math
import re
from datetime import datetime, timezone

from sqlalchemy.orm import Session, selectinload

from app.models.candidate import Candidate, CandidateLanguage, CandidateRepository

# ---------------------------------------------------------------------------
# Language / keyword dictionaries
# ---------------------------------------------------------------------------

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
}

TECH_KEYWORDS: set[str] = {
    "api", "rest", "restful", "graphql", "grpc", "microservices", "distributed",
    "event-driven", "serverless",
    "frontend", "react", "vue", "angular", "svelte", "nextjs", "next.js",
    "html", "css", "tailwind", "webpack", "vite",
    "backend", "server", "fastapi", "django", "flask", "express", "node",
    "nodejs", "spring", "rails", "laravel", "gin", "fiber", "actix",
    "sql", "nosql", "postgresql", "postgres", "mysql", "sqlite", "mongodb",
    "redis", "elasticsearch", "kafka", "rabbitmq", "celery", "database",
    "aws", "gcp", "azure", "cloud", "docker", "kubernetes", "k8s",
    "terraform", "ci/cd", "github actions", "linux", "devops",
    "full-stack", "fullstack",
    "machine learning", "ml", "deep learning", "nlp", "llm", "ai",
    "data science", "pytorch", "tensorflow", "scikit",
    "testing", "unit test", "integration test", "tdd", "agile", "startup",
    "open source", "scalable", "performance", "security",
    "junior", "senior", "lead", "principal", "staff",
}

# Keyword groups used to generate targeted concerns
CONCERN_GROUPS: dict[str, set[str]] = {
    "SQL/database": {"sql", "postgresql", "postgres", "mysql", "sqlite", "database", "nosql", "mongodb"},
    "cloud/deployment": {"aws", "gcp", "azure", "cloud", "docker", "kubernetes", "k8s", "terraform", "devops"},
    "testing": {"testing", "unit test", "tdd", "integration test"},
}


# ---------------------------------------------------------------------------
# Parsing helpers
# ---------------------------------------------------------------------------

def extract_languages(jd: str) -> list[str]:
    norm = jd.lower()
    found: list[str] = []
    seen: set[str] = set()
    for keyword, canonical in LANGUAGE_MAP.items():
        if re.search(rf"\b{re.escape(keyword)}\b", norm) and canonical not in seen:
            found.append(canonical)
            seen.add(canonical)
    return found


def extract_keywords(jd: str) -> list[str]:
    norm = jd.lower()
    return [kw for kw in TECH_KEYWORDS if kw in norm]


# ---------------------------------------------------------------------------
# Sub-score calculations (each returns 0–100)
# ---------------------------------------------------------------------------

def _language_score(candidate_languages: list[CandidateLanguage], jd_languages: list[str]) -> float:
    if not jd_languages or not candidate_languages:
        return 0.0
    lang_map = {l.language.lower(): l.repo_count for l in candidate_languages}
    total_repos = sum(lang_map.values()) or 1
    matched_repos = sum(lang_map.get(jd_lang.lower(), 0) for jd_lang in jd_languages)
    return min(100.0, (matched_repos / total_repos) * 100)


def _keyword_score(candidate: Candidate, repos: list[CandidateRepository], jd_keywords: list[str]) -> tuple[float, list[str]]:
    """Returns (score 0–100, list of matched keywords)."""
    if not jd_keywords:
        return 0.0, []
    corpus = " ".join(filter(None, [
        candidate.bio or "",
        candidate.company or "",
        *[r.description or "" for r in repos],
        *[r.name or "" for r in repos],
    ])).lower()
    found = [kw for kw in jd_keywords if kw in corpus]
    score = min(100.0, len(found) / max(len(jd_keywords), 1) * 100)
    return score, found


def _activity_score(repos: list[CandidateRepository]) -> float:
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
        scores.append(100.0 * math.exp(-days_ago / 365))
    return max(scores) if scores else 0.0


def _count_recent_repos(repos: list[CandidateRepository], days: int = 180) -> int:
    now = datetime.now(timezone.utc)
    count = 0
    for repo in repos:
        if not repo.pushed_at:
            continue
        try:
            pushed = datetime.fromisoformat(repo.pushed_at.replace("Z", "+00:00"))
            if (now - pushed).days <= days:
                count += 1
        except ValueError:
            continue
    return count


def _follower_score(followers: int) -> float:
    if followers <= 0:
        return 0.0
    lo, hi = math.log(20), math.log(2000)
    clamped = min(max(math.log(followers + 1), lo), hi)
    return (clamped - lo) / (hi - lo) * 100


def _completeness_score(profile_completeness: str | None) -> float:
    return {"high": 100.0, "medium": 60.0, "low": 20.0}.get(profile_completeness or "", 0.0)


def _repo_quality_score(repos: list[CandidateRepository]) -> float:
    if not repos:
        return 0.0
    described = sum(1 for r in repos if r.description and len(r.description) > 20)
    total_stars = sum(r.stars for r in repos)
    desc_score = min(50.0, (described / max(len(repos), 1)) * 100 * 0.5)
    star_score = min(40.0, math.log(total_stars + 1) / math.log(100) * 40) if total_stars > 0 else 0.0
    count_score = 10.0 if len(repos) >= 5 else 5.0
    return min(100.0, desc_score + star_score + count_score)


# ---------------------------------------------------------------------------
# Evidence and concerns generation
# ---------------------------------------------------------------------------

def _build_evidence(
    candidate: Candidate,
    repos: list[CandidateRepository],
    matched_languages: list[str],
    found_keywords: list[str],
    recent_count: int,
) -> list[str]:
    ev: list[str] = []

    for lang in matched_languages:
        count = next((l.repo_count for l in candidate.languages if l.language.lower() == lang.lower()), 0)
        noun = "repository" if count == 1 else "repositories"
        ev.append(f"{lang} appears in {count} {noun}")

    if found_keywords:
        shown = found_keywords[:5]
        ev.append(f"Keywords found in profile/repos: {', '.join(shown)}")

    if recent_count > 0:
        noun = "repository" if recent_count == 1 else "repositories"
        ev.append(f"{recent_count} {noun} pushed in the last 6 months")

    starred = [r for r in repos if r.stars >= 5]
    if starred:
        noun = "repository" if len(starred) == 1 else "repositories"
        ev.append(f"{len(starred)} {noun} with notable GitHub stars")

    if candidate.profile_completeness == "high":
        ev.append("Profile is highly complete (name, bio, location all present)")

    return ev


def _build_concerns(
    jd_languages: list[str],
    jd_keywords: list[str],
    matched_languages: list[str],
    found_keywords: list[str],
    recent_count: int,
    profile_completeness: str | None,
) -> list[str]:
    concerns: list[str] = []

    missing_langs = [l for l in jd_languages if l not in matched_languages]
    for lang in missing_langs[:3]:
        concerns.append(f"No explicit {lang} signal found in profile or repositories")

    for category, kws in CONCERN_GROUPS.items():
        jd_wants = any(kw in jd_keywords for kw in kws)
        candidate_has = any(kw in found_keywords for kw in kws)
        if jd_wants and not candidate_has:
            concerns.append(f"No explicit {category} signal found")

    if recent_count == 0:
        concerns.append("No repository activity found in the last 6 months")

    if profile_completeness == "low":
        concerns.append("Profile is incomplete — limited signal available")

    return concerns


def _build_summary(final_score: float, matched_languages: list[str]) -> str:
    if final_score >= 75:
        level = "Strong"
    elif final_score >= 55:
        level = "Moderate"
    elif final_score >= 35:
        level = "Partial"
    else:
        level = "Limited"

    lang_str = f" with {'/'.join(matched_languages[:2])} signal" if matched_languages else ""
    return f"{level} technical match{lang_str} based on public GitHub data."


# ---------------------------------------------------------------------------
# Main scoring entry point
# ---------------------------------------------------------------------------

def score_candidate(
    candidate: Candidate,
    jd_languages: list[str],
    jd_keywords: list[str],
) -> dict:
    repos = candidate.repositories

    lang_score = _language_score(candidate.languages, jd_languages)
    kw_score, found_keywords = _keyword_score(candidate, repos, jd_keywords)
    act_score = _activity_score(repos)
    fol_score = _follower_score(candidate.followers or 0)
    comp_score = _completeness_score(candidate.profile_completeness)
    repo_q_score = _repo_quality_score(repos)
    recent_count = _count_recent_repos(repos, days=180)

    # Weighted contribution — sums to 100 pts max
    tech_pts = lang_score * 0.30 + kw_score * 0.20        # max 50
    act_pts = act_score * 0.25                              # max 25
    profile_pts = comp_score * 0.10 + fol_score * 0.05    # max 15
    repo_pts = repo_q_score * 0.10                         # max 10

    final_score = tech_pts + act_pts + profile_pts + repo_pts

    matched_languages = [
        lang for lang in jd_languages
        if any(l.language.lower() == lang.lower() for l in candidate.languages)
    ]

    breakdown = [
        {"label": "Technical match", "score": round(tech_pts, 1), "max": 50},
        {"label": "Activity signal", "score": round(act_pts, 1), "max": 25},
        {"label": "Profile signal",  "score": round(profile_pts, 1), "max": 15},
        {"label": "Repo quality",    "score": round(repo_pts, 1), "max": 10},
    ]

    evidence = _build_evidence(candidate, repos, matched_languages, found_keywords, recent_count)
    concerns = _build_concerns(jd_languages, jd_keywords, matched_languages, found_keywords, recent_count, candidate.profile_completeness)
    summary = _build_summary(final_score, matched_languages)

    return {
        "heuristic_score": round(final_score, 1),
        "final_score": round(final_score, 1),
        "technical_match": round(tech_pts, 1),
        "activity_signal": round(act_pts, 1),
        "profile_completeness_score": round(profile_pts, 1),
        "breakdown": breakdown,
        "evidence": evidence,
        "concerns": concerns,
        "summary": summary,
    }


def score_all_candidates(db: Session, job_description: str) -> list[dict]:
    jd_languages = extract_languages(job_description)
    jd_keywords = extract_keywords(job_description)

    candidates = (
        db.query(Candidate)
        .options(selectinload(Candidate.languages), selectinload(Candidate.repositories))
        .all()
    )

    results = [
        {"candidate": c, **score_candidate(c, jd_languages, jd_keywords)}
        for c in candidates
    ]
    results.sort(key=lambda r: r["final_score"], reverse=True)
    return results

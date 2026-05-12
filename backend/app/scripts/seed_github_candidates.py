import argparse
import sys
import time
from collections import Counter
from pathlib import Path

import httpx

BACKEND_DIR = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(BACKEND_DIR))

from app.core.config import settings
from app.core.database import Base, SessionLocal, engine
from app.models.candidate import Candidate, CandidateLanguage, CandidateRepository

GITHUB_API = "https://api.github.com"

SEARCH_QUERIES = [
    "language:python followers:20..1999 repos:5..100 type:user",
    "language:typescript followers:20..1999 repos:5..100 type:user",
    "language:go followers:10..1999 repos:3..100 type:user",
    "language:java followers:15..1999 repos:5..100 type:user",
    "language:rust followers:10..1999 repos:3..100 type:user",
    'location:"New York" language:python followers:10..1999 repos:3..100 type:user',
    'location:"San Francisco" language:typescript followers:10..1999 repos:3..100 type:user',
    'location:"London" language:python followers:10..1999 repos:3..100 type:user',
    'location:"Seattle" language:go followers:10..1999 repos:3..100 type:user',
]

MAX_REPOS_PER_CANDIDATE = 10
MAX_FOLLOWERS = 2000
MIN_PUBLIC_REPOS = 3
MAX_PUBLIC_REPOS = 150


def _headers() -> dict:
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }

    if settings.GITHUB_TOKEN:
        headers["Authorization"] = f"Bearer {settings.GITHUB_TOKEN}"

    return headers


def _get(client: httpx.Client, url: str, params: dict | None = None) -> dict | list | None:
    for attempt in range(3):
        resp = client.get(url, params=params, headers=_headers(), timeout=20)

        if resp.status_code == 200:
            return resp.json()

        if resp.status_code == 403:
            reset = int(resp.headers.get("X-RateLimit-Reset", time.time() + 60))
            wait = max(reset - int(time.time()), 1)
            print(f"  Rate limited. Waiting {wait}s...")
            time.sleep(wait)
            continue

        if resp.status_code == 404:
            return None

        print(f"  HTTP {resp.status_code} for {url} — skipping")
        try:
            print(f"  Response: {resp.json()}")
        except Exception:
            print(f"  Response: {resp.text[:300]}")
        return None

    print(f"  Failed after retries: {url}")
    return None


def _profile_completeness(user: dict) -> str:
    score = 0

    if user.get("name"):
        score += 1
    if user.get("bio"):
        score += 1
    if user.get("location"):
        score += 1
    if user.get("company"):
        score += 1
    if user.get("blog"):
        score += 1

    if score >= 4:
        return "high"
    if score >= 2:
        return "medium"
    return "low"


def _fetch_repos(client: httpx.Client, username: str) -> list[dict]:
    data = _get(
        client,
        f"{GITHUB_API}/users/{username}/repos",
        params={
            "sort": "pushed",
            "direction": "desc",
            "per_page": MAX_REPOS_PER_CANDIDATE,
            "type": "owner",
        },
    )

    if not isinstance(data, list):
        return []

    # Forks are less useful as candidate signal.
    return [repo for repo in data if not repo.get("fork")]


def _aggregate_languages(repos: list[dict]) -> Counter:
    counter: Counter = Counter()

    for repo in repos:
        lang = repo.get("language")
        if lang:
            counter[lang] += 1

    return counter


def _skip_reason(user: dict, repos: list[dict]) -> str | None:
    if user.get("type") != "User":
        return "not an individual user"

    followers = user.get("followers", 0) or 0
    public_repos = user.get("public_repos", 0) or 0

    if followers >= MAX_FOLLOWERS:
        return f"{followers} followers"

    if public_repos < MIN_PUBLIC_REPOS:
        return f"only {public_repos} public repos"

    if public_repos > MAX_PUBLIC_REPOS:
        return f"{public_repos} public repos"

    if not (user.get("name") or user.get("bio")):
        return "missing name and bio"

    if not repos:
        return "no usable non-fork repos"

    return None


def _upsert_candidate(db, user: dict, repos: list[dict]) -> Candidate:
    lang_counts = _aggregate_languages(repos)

    existing = db.query(Candidate).filter_by(github_id=user["id"]).first()

    if existing:
        candidate = existing
    else:
        candidate = Candidate(github_id=user["id"])
        db.add(candidate)

    candidate.github_username = user["login"]
    candidate.name = user.get("name")
    candidate.avatar_url = user.get("avatar_url")
    candidate.profile_url = user.get("html_url")
    candidate.bio = user.get("bio")
    candidate.company = user.get("company")
    candidate.location = user.get("location")
    candidate.followers = user.get("followers", 0) or 0
    candidate.following = user.get("following", 0) or 0
    candidate.public_repos = user.get("public_repos", 0) or 0
    candidate.profile_completeness = _profile_completeness(user)

    db.flush()

    # Replace repositories for this candidate.
    db.query(CandidateRepository).filter_by(candidate_id=candidate.id).delete()

    for repo in repos:
        db.add(
            CandidateRepository(
                candidate_id=candidate.id,
                github_repo_id=repo["id"],
                name=repo.get("name") or "",
                description=repo.get("description"),
                url=repo.get("html_url"),
                language=repo.get("language"),
                stars=repo.get("stargazers_count", 0) or 0,
                forks=repo.get("forks_count", 0) or 0,
                pushed_at=repo.get("pushed_at"),
            )
        )

    # Replace language aggregates for this candidate.
    db.query(CandidateLanguage).filter_by(candidate_id=candidate.id).delete()

    for lang, count in lang_counts.items():
        db.add(
            CandidateLanguage(
                candidate_id=candidate.id,
                language=lang,
                repo_count=count,
            )
        )

    return candidate


def search_candidates(client: httpx.Client, query: str, per_page: int = 100) -> list[str]:
    """Return GitHub logins from a search query."""
    data = _get(
        client,
        f"{GITHUB_API}/search/users",
        params={
            "q": query,
            "per_page": per_page,
        },
    )

    if not isinstance(data, dict) or "items" not in data:
        return []

    return [item["login"] for item in data["items"]]


def collect_candidate_logins(client: httpx.Client, target: int) -> list[str]:
    seen_logins: set[str] = set()
    logins_to_fetch: list[str] = []

    # Collect more than target because some profiles will be skipped after full fetch.
    max_to_collect = target * 4

    print(f"Collecting candidate logins. Target saved candidates: {target}")

    for query in SEARCH_QUERIES:
        if len(logins_to_fetch) >= max_to_collect:
            break

        print(f"  Searching: {query}")
        logins = search_candidates(client, query, per_page=100)

        for login in logins:
            if login not in seen_logins:
                seen_logins.add(login)
                logins_to_fetch.append(login)

            if len(logins_to_fetch) >= max_to_collect:
                break

        # GitHub Search API has stricter rate limits than normal REST endpoints.
        time.sleep(1.2)

    return logins_to_fetch


def run(target: int = 100) -> None:
    print("Creating tables if needed...")
    Base.metadata.create_all(bind=engine)

    with httpx.Client() as client:
        logins_to_fetch = collect_candidate_logins(client, target)

        print(f"Collected {len(logins_to_fetch)} candidate logins.")
        print(f"Fetching profiles until {target} candidates are saved...")

        db = SessionLocal()

        saved_count = 0
        skipped_count = 0
        failed_count = 0

        try:
            for i, login in enumerate(logins_to_fetch, 1):
                if saved_count >= target:
                    break

                print(f"  [{i}/{len(logins_to_fetch)}] {login}")

                user = _get(client, f"{GITHUB_API}/users/{login}")

                if not user or not isinstance(user, dict):
                    failed_count += 1
                    print(f"    Failed to fetch user profile")
                    continue

                repos = _fetch_repos(client, login)

                reason = _skip_reason(user, repos)
                if reason:
                    skipped_count += 1
                    print(f"    Skipping {login} ({reason})")
                    continue

                try:
                    _upsert_candidate(db, user, repos)
                    db.commit()

                    saved_count += 1
                    print(f"    Saved {login} ({saved_count}/{target})")

                except Exception as exc:
                    db.rollback()
                    failed_count += 1
                    print(f"    Failed to save {login}: {exc}")

                # Stay comfortably under authenticated REST API limits.
                time.sleep(0.5)

        finally:
            db.close()

    print("\nDone.")
    print(f"  Saved:   {saved_count}")
    print(f"  Skipped: {skipped_count}")
    print(f"  Failed:  {failed_count}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed GitHub candidates into the database.")
    parser.add_argument("--limit", type=int, default=100, help="Max candidates to save")
    args = parser.parse_args()

    run(target=args.limit)
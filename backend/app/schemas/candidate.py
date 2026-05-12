from datetime import datetime

from pydantic import BaseModel, ConfigDict


class CandidateRepository(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: str | None
    url: str | None
    language: str | None
    stars: int
    forks: int
    pushed_at: str | None


class CandidateLanguage(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    language: str
    repo_count: int


class CandidateSummary(BaseModel):
    """Lightweight shape returned in list responses."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    github_username: str
    name: str | None
    avatar_url: str | None
    profile_url: str | None
    bio: str | None
    location: str | None
    company: str | None
    followers: int
    public_repos: int
    profile_completeness: str | None
    top_languages: list[CandidateLanguage] = []


class CandidateDetail(CandidateSummary):
    """Full shape returned in single-candidate responses."""
    following: int
    repositories: list[CandidateRepository] = []
    languages: list[CandidateLanguage] = []
    created_at: datetime | None

from app.models.candidate import Candidate
from app.schemas.candidate import CandidateLanguage, CandidateSummary


def candidate_to_summary(candidate: Candidate) -> CandidateSummary:
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
        top_languages=[
            CandidateLanguage(language=l.language, repo_count=l.repo_count)
            for l in top_languages
        ],
    )

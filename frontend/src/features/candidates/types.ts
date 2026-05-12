export interface CandidateLanguage {
  language: string;
  repo_count: number;
}

export interface CandidateRepository {
  id: number;
  name: string;
  description: string | null;
  url: string | null;
  language: string | null;
  stars: number;
  forks: number;
  pushed_at: string | null;
}

export interface CandidateSummary {
  id: number;
  github_username: string;
  name: string | null;
  avatar_url: string | null;
  profile_url: string | null;
  bio: string | null;
  location: string | null;
  company: string | null;
  followers: number;
  public_repos: number;
  profile_completeness: string | null;
  top_languages: CandidateLanguage[];
}

export interface CandidateDetail extends CandidateSummary {
  following: number;
  repositories: CandidateRepository[];
  languages: CandidateLanguage[];
  created_at: string | null;
}

export interface CandidateFilters {
  q: string;
  language: string;
  location: string;
  min_followers: string;
  max_followers: string;
  min_repos: string;
  profile_completeness: string;
}

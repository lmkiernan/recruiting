import type { CandidateDetail, CandidateFilters, CandidateSummary } from "./types";

const BASE = "/api";

function buildParams(filters: Partial<CandidateFilters>): URLSearchParams {
  const p = new URLSearchParams();
  if (filters.q) p.set("q", filters.q);
  if (filters.language) p.set("language", filters.language);
  if (filters.location) p.set("location", filters.location);
  if (filters.min_followers) p.set("min_followers", filters.min_followers);
  if (filters.max_followers) p.set("max_followers", filters.max_followers);
  if (filters.min_repos) p.set("min_repos", filters.min_repos);
  if (filters.profile_completeness) p.set("profile_completeness", filters.profile_completeness);
  return p;
}

export async function fetchCandidates(
  filters: Partial<CandidateFilters> = {}
): Promise<CandidateSummary[]> {
  const params = buildParams(filters);
  const res = await fetch(`${BASE}/candidates?${params}`);
  if (!res.ok) throw new Error(`Failed to fetch candidates: ${res.status}`);
  return res.json() as Promise<CandidateSummary[]>;
}

export async function fetchCandidate(id: number): Promise<CandidateDetail> {
  const res = await fetch(`${BASE}/candidates/${id}`);
  if (!res.ok) throw new Error(`Failed to fetch candidate ${id}: ${res.status}`);
  return res.json() as Promise<CandidateDetail>;
}

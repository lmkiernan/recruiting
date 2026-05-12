import { apiFetch, BASE } from "../../lib/apiFetch";
import type { CandidateDetail, CandidateFilters, CandidateSummary } from "./types";

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
  const res = await apiFetch(`${BASE}/candidates?${buildParams(filters)}`);
  return res.json() as Promise<CandidateSummary[]>;
}

export async function fetchCandidate(id: number): Promise<CandidateDetail> {
  const res = await apiFetch(`${BASE}/candidates/${id}`);
  return res.json() as Promise<CandidateDetail>;
}

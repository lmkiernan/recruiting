import { useEffect, useState } from "react";
import { fetchCandidate, fetchCandidates } from "./api";
import type { CandidateDetail, CandidateFilters, CandidateSummary } from "./types";

export function useCandidates(filters: Partial<CandidateFilters>) {
  const [candidates, setCandidates] = useState<CandidateSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    fetchCandidates(filters)
      .then((data) => { if (!cancelled) setCandidates(data); })
      .catch((e: unknown) => {
        if (!cancelled) setError(e instanceof Error ? e.message : "Unknown error");
      })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [JSON.stringify(filters)]);

  return { candidates, loading, error };
}

export function useCandidateDetail(id: number | null) {
  const [candidate, setCandidate] = useState<CandidateDetail | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (id === null) { setCandidate(null); return; }
    let cancelled = false;
    setLoading(true);
    setError(null);
    fetchCandidate(id)
      .then((data) => { if (!cancelled) setCandidate(data); })
      .catch((e: unknown) => {
        if (!cancelled) setError(e instanceof Error ? e.message : "Unknown error");
      })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [id]);

  return { candidate, loading, error };
}

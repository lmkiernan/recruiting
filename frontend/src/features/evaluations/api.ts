import type { CandidateEvaluation, EvaluationRunWithResults } from "./types";

const BASE = "/api";

async function apiFetch(input: RequestInfo, init?: RequestInit): Promise<Response> {
  const res = await fetch(input, init).catch(() => {
    throw new Error("Network error — could not reach the server");
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error((body as { detail?: string }).detail ?? `Request failed: ${res.status}`);
  }
  return res;
}

async function createJob(description: string, title?: string): Promise<{ id: number }> {
  const res = await apiFetch(`${BASE}/jobs`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ description, title: title ?? null }),
  });
  return res.json() as Promise<{ id: number }>;
}

async function createEvaluationRun(jobId: number): Promise<EvaluationRunWithResults> {
  const res = await apiFetch(`${BASE}/evaluation-runs`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ job_id: jobId }),
  });
  return res.json() as Promise<EvaluationRunWithResults>;
}

export async function runEvaluation(description: string): Promise<EvaluationRunWithResults> {
  const job = await createJob(description);
  return createEvaluationRun(job.id);
}

export async function fetchRunStatus(runId: number): Promise<{ status: string; completed_count: number; candidate_count: number }> {
  const res = await apiFetch(`${BASE}/evaluation-runs/${runId}`);
  return res.json();
}

export async function fetchRunCandidates(runId: number): Promise<CandidateEvaluation[]> {
  const res = await apiFetch(`${BASE}/evaluation-runs/${runId}/candidates`);
  return res.json() as Promise<CandidateEvaluation[]>;
}

export async function summarizeCandidateEval(evalId: number): Promise<CandidateEvaluation> {
  const res = await apiFetch(`${BASE}/candidate-evaluations/${evalId}/ai-summarize`, {
    method: "POST",
  });
  return res.json() as Promise<CandidateEvaluation>;
}

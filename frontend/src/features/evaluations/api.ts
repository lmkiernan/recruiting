import type { CandidateEvaluation, EvaluationRunWithResults } from "./types";

const BASE = "/api";

async function createJob(description: string, title?: string): Promise<{ id: number }> {
  const res = await fetch(`${BASE}/jobs`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ description, title: title ?? null }),
  });
  if (!res.ok) throw new Error(`Failed to create job: ${res.status}`);
  return res.json() as Promise<{ id: number }>;
}

async function createEvaluationRun(jobId: number): Promise<EvaluationRunWithResults> {
  const res = await fetch(`${BASE}/evaluation-runs`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ job_id: jobId }),
  });
  if (!res.ok) throw new Error(`Failed to create evaluation run: ${res.status}`);
  return res.json() as Promise<EvaluationRunWithResults>;
}

export async function runEvaluation(description: string): Promise<EvaluationRunWithResults> {
  const job = await createJob(description);
  return createEvaluationRun(job.id);
}

export async function fetchRunStatus(runId: number): Promise<{ status: string; completed_count: number; candidate_count: number }> {
  const res = await fetch(`${BASE}/evaluation-runs/${runId}`);
  if (!res.ok) throw new Error(`Failed to fetch run status: ${res.status}`);
  return res.json();
}

export async function fetchRunCandidates(runId: number): Promise<CandidateEvaluation[]> {
  const res = await fetch(`${BASE}/evaluation-runs/${runId}/candidates`);
  if (!res.ok) throw new Error(`Failed to fetch run candidates: ${res.status}`);
  return res.json() as Promise<CandidateEvaluation[]>;
}

export async function summarizeCandidateEval(evalId: number): Promise<CandidateEvaluation> {
  const res = await fetch(`${BASE}/candidate-evaluations/${evalId}/ai-summarize`, {
    method: "POST",
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error((body as { detail?: string }).detail ?? `Summarize failed: ${res.status}`);
  }
  return res.json() as Promise<CandidateEvaluation>;
}

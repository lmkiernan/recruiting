import type { EvaluationRunWithResults } from "./types";

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

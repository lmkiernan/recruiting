import type { CandidateSummary } from "../candidates/types";

export interface CandidateEvaluation {
  id: number;
  candidate_id: number;
  heuristic_score: number | null;
  final_score: number | null;
  technical_match: number | null;
  activity_signal: number | null;
  profile_completeness_score: number | null;
  status: string;
  candidate: CandidateSummary;
}

export interface EvaluationRunWithResults {
  id: number;
  job_id: number;
  status: string;
  candidate_count: number;
  completed_count: number;
  created_at: string;
  completed_at: string | null;
  evaluations: CandidateEvaluation[];
}

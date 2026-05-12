import { useCallback, useEffect, useRef, useState } from "react";
import { fetchRunCandidates, fetchRunStatus } from "./api";
import type { CandidateEvaluation } from "./types";

const POLL_INTERVAL_MS = 3000;
const TERMINAL_STATUSES = new Set(["completed", "ai_failed"]);

interface PollState {
  status: string;
  completedCount: number;
  candidateCount: number;
  evaluations: CandidateEvaluation[];
}

export function useEvaluationPolling(
  runId: number | null,
  initialStatus: string,
  onUpdate: (state: PollState) => void,
) {
  const active = useRef(false);
  const [polling, setPolling] = useState(false);

  const stop = useCallback(() => {
    active.current = false;
    setPolling(false);
  }, []);

  useEffect(() => {
    if (runId === null || TERMINAL_STATUSES.has(initialStatus)) return;

    active.current = true;
    setPolling(true);

    async function tick() {
      if (!active.current || runId === null) return;

      try {
        const [runInfo, candidates] = await Promise.all([
          fetchRunStatus(runId),
          fetchRunCandidates(runId),
        ]);

        if (!active.current) return;

        onUpdate({
          status: runInfo.status,
          completedCount: runInfo.completed_count,
          candidateCount: runInfo.candidate_count,
          evaluations: candidates,
        });

        if (TERMINAL_STATUSES.has(runInfo.status)) {
          stop();
        } else {
          setTimeout(tick, POLL_INTERVAL_MS);
        }
      } catch {
        if (active.current) setTimeout(tick, POLL_INTERVAL_MS);
      }
    }

    setTimeout(tick, POLL_INTERVAL_MS);
    return stop;
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [runId]);

  return { polling, stop };
}

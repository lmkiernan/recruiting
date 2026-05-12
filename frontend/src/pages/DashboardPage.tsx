import { useState } from "react";
import { JobDescriptionInput } from "../components/jobs/JobDescriptionInput";
import { CandidateCard } from "../components/candidates/CandidateCard";
import { CandidateDetailPanel } from "../components/candidates/CandidateDetailPanel";
import { CandidateFiltersPanel } from "../components/candidates/CandidateFilters";
import { EmptyState } from "../components/ui/EmptyState";
import { ErrorState } from "../components/ui/ErrorState";
import { Spinner } from "../components/ui/Spinner";
import { runEvaluation } from "../features/evaluations/api";
import type { EvaluationRunWithResults } from "../features/evaluations/types";
import { useCandidates } from "../features/candidates/hooks";
import type { CandidateFilters } from "../features/candidates/types";

const EMPTY_FILTERS: CandidateFilters = {
  q: "",
  language: "",
  location: "",
  min_followers: "",
  max_followers: "",
  min_repos: "",
  profile_completeness: "",
};

export function DashboardPage() {
  const [filters, setFilters] = useState<CandidateFilters>(EMPTY_FILTERS);
  const [searchInput, setSearchInput] = useState("");
  const [selectedId, setSelectedId] = useState<number | null>(null);

  const [jobDescription, setJobDescription] = useState("");
  const [evaluating, setEvaluating] = useState(false);
  const [evalError, setEvalError] = useState<string | null>(null);
  const [evalRun, setEvalRun] = useState<EvaluationRunWithResults | null>(null);

  const isEvalMode = evalRun !== null;

  // Browse mode — fetch from backend with filters
  const browseFilters = { ...filters, q: searchInput };
  const { candidates, loading: browseLoading, error: browseError } = useCandidates(
    isEvalMode ? null : browseFilters
  );

  async function handleEvaluate() {
    if (!jobDescription.trim()) return;
    setEvaluating(true);
    setEvalError(null);
    setSelectedId(null);
    try {
      const result = await runEvaluation(jobDescription);
      setEvalRun(result);
    } catch (e) {
      setEvalError(e instanceof Error ? e.message : "Evaluation failed");
    } finally {
      setEvaluating(false);
    }
  }

  function handleClearEval() {
    setEvalRun(null);
    setEvalError(null);
    setSelectedId(null);
  }

  // In eval mode: use ranked results, filter client-side by search input
  const evalItems = evalRun
    ? evalRun.evaluations.filter((ev) => {
        if (!searchInput) return true;
        const term = searchInput.toLowerCase();
        const c = ev.candidate;
        return (
          c.github_username.toLowerCase().includes(term) ||
          (c.name ?? "").toLowerCase().includes(term) ||
          (c.bio ?? "").toLowerCase().includes(term) ||
          (c.location ?? "").toLowerCase().includes(term)
        );
      })
    : [];

  const listLoading = isEvalMode ? evaluating : browseLoading;
  const listError = isEvalMode ? evalError : browseError;
  const listCount = isEvalMode ? evalItems.length : candidates.length;

  return (
    <div className="flex h-screen overflow-hidden bg-gray-50">
      {/* Left sidebar */}
      <aside className="w-64 shrink-0 border-r border-gray-200 bg-white flex flex-col">
        <div className="px-4 py-4 border-b border-gray-100">
          <h1 className="text-sm font-semibold text-gray-900">Recruiter Signal</h1>
          <p className="text-xs text-gray-400 mt-0.5">GitHub candidate pool</p>
        </div>
        <div className="p-4 flex-1 overflow-y-auto space-y-6">
          <JobDescriptionInput
            value={jobDescription}
            onChange={setJobDescription}
            onEvaluate={handleEvaluate}
            onClear={handleClearEval}
            evaluating={evaluating}
            hasResults={isEvalMode}
          />
          {!isEvalMode && (
            <div>
              <p className="text-xs font-semibold text-gray-700 uppercase tracking-wide mb-3">Filters</p>
              <CandidateFiltersPanel filters={filters} onChange={setFilters} />
            </div>
          )}
        </div>
      </aside>

      {/* Center — candidate list */}
      <main className="flex-1 flex flex-col min-w-0 border-r border-gray-200">
        {/* Eval mode banner */}
        {isEvalMode && (
          <div className="px-4 py-2 bg-blue-50 border-b border-blue-100 flex items-center justify-between gap-2">
            <p className="text-xs text-blue-700 truncate">
              <span className="font-medium">Ranked by match</span>
              {" · "}
              {evalRun.completed_count} candidates scored
            </p>
            <button onClick={handleClearEval} className="text-xs text-blue-400 hover:text-blue-600 shrink-0">
              ✕ Clear
            </button>
          </div>
        )}

        {/* Search bar */}
        <div className="px-4 py-3 border-b border-gray-200 bg-white">
          <input
            type="search"
            placeholder="Search by name, username, bio, location…"
            value={searchInput}
            onChange={(e) => setSearchInput(e.target.value)}
            className="w-full text-sm border border-gray-200 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-400"
          />
          <p className="mt-1.5 text-xs text-gray-400">
            {listLoading ? "Loading…" : `${listCount} candidate${listCount !== 1 ? "s" : ""}`}
          </p>
        </div>

        {/* List */}
        <div className="flex-1 overflow-y-auto p-3 space-y-2">
          {listLoading && <Spinner />}
          {!listLoading && listError && <ErrorState message={listError} />}

          {/* Eval mode */}
          {!listLoading && !listError && isEvalMode && (
            <>
              {evalItems.length === 0 && <EmptyState />}
              {evalItems.map((ev) => (
                <CandidateCard
                  key={ev.candidate_id}
                  candidate={ev.candidate}
                  selected={selectedId === ev.candidate_id}
                  onClick={() => setSelectedId(ev.candidate_id)}
                  score={ev.final_score}
                />
              ))}
            </>
          )}

          {/* Browse mode */}
          {!listLoading && !listError && !isEvalMode && (
            <>
              {candidates.length === 0 && <EmptyState />}
              {candidates.map((c) => (
                <CandidateCard
                  key={c.id}
                  candidate={c}
                  selected={selectedId === c.id}
                  onClick={() => setSelectedId(c.id)}
                />
              ))}
            </>
          )}
        </div>
      </main>

      {/* Right — detail panel */}
      <aside className="w-96 shrink-0 bg-white overflow-hidden">
        <CandidateDetailPanel candidateId={selectedId} />
      </aside>
    </div>
  );
}

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { JobDescriptionInput } from "../components/jobs/JobDescriptionInput";
import { CandidateCard } from "../components/candidates/CandidateCard";
import { CandidateDetailPanel } from "../components/candidates/CandidateDetailPanel";
import { CandidateFiltersPanel } from "../components/candidates/CandidateFilters";
import { EmptyState } from "../components/ui/EmptyState";
import { ErrorState } from "../components/ui/ErrorState";
import { Spinner } from "../components/ui/Spinner";
import { runEvaluation } from "../features/evaluations/api";
import { useEvaluationPolling } from "../features/evaluations/hooks";
import type { CandidateEvaluation, EvaluationRunWithResults } from "../features/evaluations/types";
import { useCandidates } from "../features/candidates/hooks";
import { fetchCandidate } from "../features/candidates/api";
import type { CandidateDetail, CandidateFilters } from "../features/candidates/types";
import { useShortlist } from "../features/shortlists/ShortlistContext";

type View = "browse" | "shortlist";

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
  const [view, setView] = useState<View>("browse");
  const [filters, setFilters] = useState<CandidateFilters>(EMPTY_FILTERS);
  const [searchInput, setSearchInput] = useState("");
  const [selectedId, setSelectedId] = useState<number | null>(null);

  const [jobDescription, setJobDescription] = useState("");
  const [evaluating, setEvaluating] = useState(false);
  const [evalError, setEvalError] = useState<string | null>(null);
  const [evalRun, setEvalRun] = useState<EvaluationRunWithResults | null>(null);

  const isEvalMode = evalRun !== null;
  const isAiRunning = evalRun?.status === "heuristic_complete";

  // ---------------------------------------------------------------------------
  // Shortlist view — cache fetched candidates, only load new IDs
  // ---------------------------------------------------------------------------
  const { savedIds, count } = useShortlist();
  const [shortlistCache, setShortlistCache] = useState<Record<number, CandidateDetail>>({});
  const [shortlistLoading, setShortlistLoading] = useState(false);
  const [shortlistError, setShortlistError] = useState<string | null>(null);
  const loadingRef = useRef(false);

  useEffect(() => {
    if (view !== "shortlist" || savedIds.length === 0) return;
    const unloaded = savedIds.filter((id) => !(id in shortlistCache));
    if (unloaded.length === 0 || loadingRef.current) return;

    loadingRef.current = true;
    setShortlistLoading(true);
    setShortlistError(null);

    Promise.all(unloaded.map(fetchCandidate))
      .then((results) =>
        setShortlistCache((prev) => {
          const next = { ...prev };
          results.forEach((c) => { next[c.id] = c; });
          return next;
        }),
      )
      .catch((e) => setShortlistError(e instanceof Error ? e.message : "Failed to load candidates"))
      .finally(() => { loadingRef.current = false; setShortlistLoading(false); });
  }, [view, savedIds]); // eslint-disable-line react-hooks/exhaustive-deps

  const shortlistCandidates = useMemo(
    () => savedIds.map((id) => shortlistCache[id]).filter(Boolean) as CandidateDetail[],
    [savedIds, shortlistCache],
  );

  const filteredShortlist = useMemo(() => {
    if (!searchInput) return shortlistCandidates;
    const term = searchInput.toLowerCase();
    return shortlistCandidates.filter(
      (c) =>
        c.github_username.toLowerCase().includes(term) ||
        (c.name ?? "").toLowerCase().includes(term) ||
        (c.bio ?? "").toLowerCase().includes(term) ||
        (c.location ?? "").toLowerCase().includes(term),
    );
  }, [shortlistCandidates, searchInput]);

  // ---------------------------------------------------------------------------
  // Evaluation polling
  // ---------------------------------------------------------------------------
  const handlePollUpdate = useCallback(
    ({ status, completedCount, candidateCount, evaluations }: {
      status: string; completedCount: number; candidateCount: number; evaluations: CandidateEvaluation[];
    }) => {
      setEvalRun((prev) =>
        prev ? { ...prev, status, completed_count: completedCount, candidate_count: candidateCount, evaluations } : prev
      );
    },
    [],
  );

  useEvaluationPolling(
    isEvalMode ? evalRun.id : null,
    evalRun?.status ?? "completed",
    handlePollUpdate,
  );

  // ---------------------------------------------------------------------------
  // Browse mode
  // ---------------------------------------------------------------------------
  const { candidates, loading: browseLoading, error: browseError } = useCandidates(
    isEvalMode || view === "shortlist" ? null : { ...filters, q: searchInput }
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

  function handleSummarized(updated: CandidateEvaluation) {
    setEvalRun((prev) =>
      prev
        ? { ...prev, evaluations: prev.evaluations.map((ev) => ev.id === updated.id ? updated : ev) }
        : prev
    );
  }

  function handleViewChange(next: View) {
    setView(next);
    setSelectedId(null);
    setSearchInput("");
  }

  const evalItems = useMemo<CandidateEvaluation[]>(() => {
    if (!evalRun) return [];
    if (!searchInput) return evalRun.evaluations;
    const term = searchInput.toLowerCase();
    return evalRun.evaluations.filter((ev) => {
      const c = ev.candidate;
      return (
        c.github_username.toLowerCase().includes(term) ||
        (c.name ?? "").toLowerCase().includes(term) ||
        (c.bio ?? "").toLowerCase().includes(term) ||
        (c.location ?? "").toLowerCase().includes(term)
      );
    });
  }, [evalRun, searchInput]);

  const selectedEval = useMemo(
    () => evalRun?.evaluations.find((ev) => ev.candidate_id === selectedId) ?? null,
    [evalRun, selectedId],
  );

  // Center column derived state
  const isShortlistView = view === "shortlist";
  const listLoading = isShortlistView ? shortlistLoading : isEvalMode ? evaluating : browseLoading;
  const listError = isShortlistView ? shortlistError : isEvalMode ? evalError : browseError;
  const listCount = isShortlistView
    ? filteredShortlist.length
    : isEvalMode ? evalItems.length : candidates.length;

  return (
    <div className="flex flex-1 overflow-hidden bg-gray-50">
      {/* Left sidebar */}
      <aside className="w-64 shrink-0 border-r border-gray-200 bg-white flex flex-col">
        {/* View tabs */}
        <div className="flex border-b border-gray-200">
          <button
            onClick={() => handleViewChange("browse")}
            className={`flex-1 py-2.5 text-xs font-medium transition-colors border-b-2 ${
              view === "browse"
                ? "border-blue-500 text-blue-600"
                : "border-transparent text-gray-500 hover:text-gray-700"
            }`}
          >
            Browse
          </button>
          <button
            onClick={() => handleViewChange("shortlist")}
            className={`flex-1 py-2.5 text-xs font-medium transition-colors border-b-2 ${
              view === "shortlist"
                ? "border-blue-500 text-blue-600"
                : "border-transparent text-gray-500 hover:text-gray-700"
            }`}
          >
            Shortlisted{count > 0 ? ` (${count})` : ""}
          </button>
        </div>

        {/* Sidebar content — hidden in shortlist view */}
        {!isShortlistView && (
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
        )}

        {isShortlistView && (
          <div className="p-4 flex-1 flex flex-col justify-center items-center text-center text-gray-400">
            <svg className="w-8 h-8 mb-2 text-gray-300" fill="currentColor" viewBox="0 0 20 20">
              <path d="M5 4a2 2 0 012-2h6a2 2 0 012 2v14l-5-2.5L5 18V4z" />
            </svg>
            <p className="text-xs">
              {count === 0 ? "No candidates saved yet" : `${count} candidate${count !== 1 ? "s" : ""} saved`}
            </p>
          </div>
        )}
      </aside>

      {/* Center — candidate list */}
      <main className="flex-1 flex flex-col min-w-0 border-r border-gray-200">
        {/* Eval status banner */}
        {!isShortlistView && isEvalMode && (
          <div className={`px-4 py-2 border-b flex items-center justify-between gap-2 ${
            isAiRunning ? "bg-amber-50 border-amber-100" : "bg-blue-50 border-blue-100"
          }`}>
            <p className={`text-xs truncate ${isAiRunning ? "text-amber-700" : "text-blue-700"}`}>
              {isAiRunning ? (
                <>
                  <span className="font-medium">AI analysis running</span>
                  {evalRun.completed_count > 0 && ` · ${evalRun.completed_count}/${Math.min(evalRun.candidate_count, 25)} scored`}
                  <span className="ml-1 inline-block animate-pulse">…</span>
                </>
              ) : (
                <><span className="font-medium">AI analysis complete</span>{" · "}ranked by match</>
              )}
            </p>
            <button
              onClick={handleClearEval}
              className={`text-xs shrink-0 ${isAiRunning ? "text-amber-400 hover:text-amber-600" : "text-blue-400 hover:text-blue-600"}`}
            >
              ✕ Clear
            </button>
          </div>
        )}

        {/* Search bar */}
        <div className="px-4 py-3 border-b border-gray-200 bg-white">
          <input
            type="search"
            placeholder={isShortlistView ? "Search shortlisted candidates…" : "Search by name, username, bio, location…"}
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

          {/* Shortlist view */}
          {!listLoading && !listError && isShortlistView && (
            <>
              {filteredShortlist.length === 0 && (
                <EmptyState message={count === 0 ? "Bookmark candidates to save them here" : "No matches"} />
              )}
              {filteredShortlist.map((c) => (
                <CandidateCard
                  key={c.id}
                  candidate={c}
                  selected={selectedId === c.id}
                  onClick={() => setSelectedId(c.id)}
                />
              ))}
            </>
          )}

          {/* Eval view */}
          {!listLoading && !listError && !isShortlistView && isEvalMode && (
            <>
              {evalItems.length === 0 && <EmptyState />}
              {evalItems.map((ev) => (
                <CandidateCard
                  key={ev.candidate_id}
                  candidate={ev.candidate}
                  selected={selectedId === ev.candidate_id}
                  onClick={() => setSelectedId(ev.candidate_id)}
                  score={ev.final_score}
                  aiScored={ev.ai_score !== null}
                />
              ))}
            </>
          )}

          {/* Browse view */}
          {!listLoading && !listError && !isShortlistView && !isEvalMode && (
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
        <CandidateDetailPanel
          candidateId={selectedId}
          evaluation={selectedEval}
          onSummarized={handleSummarized}
        />
      </aside>
    </div>
  );
}

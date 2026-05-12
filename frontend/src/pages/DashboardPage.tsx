import { useState } from "react";
import { CandidateCard } from "../components/candidates/CandidateCard";
import { CandidateDetailPanel } from "../components/candidates/CandidateDetailPanel";
import { CandidateFiltersPanel } from "../components/candidates/CandidateFilters";
import { EmptyState } from "../components/ui/EmptyState";
import { ErrorState } from "../components/ui/ErrorState";
import { Spinner } from "../components/ui/Spinner";
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

  const activeFilters = { ...filters, q: searchInput };
  const { candidates, loading, error } = useCandidates(activeFilters);

  return (
    <div className="flex h-screen overflow-hidden bg-gray-50">
      {/* Left sidebar — filters */}
      <aside className="w-60 shrink-0 border-r border-gray-200 bg-white flex flex-col">
        <div className="px-4 py-4 border-b border-gray-100">
          <h1 className="text-sm font-semibold text-gray-900">Recruiter Signal</h1>
          <p className="text-xs text-gray-400 mt-0.5">GitHub candidate pool</p>
        </div>
        <div className="p-4 flex-1 overflow-y-auto">
          <CandidateFiltersPanel filters={filters} onChange={setFilters} />
        </div>
      </aside>

      {/* Center — candidate list */}
      <main className="flex-1 flex flex-col min-w-0 border-r border-gray-200">
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
            {loading ? "Loading…" : `${candidates.length} candidate${candidates.length !== 1 ? "s" : ""}`}
          </p>
        </div>

        {/* List */}
        <div className="flex-1 overflow-y-auto p-3 space-y-2">
          {loading && <Spinner />}
          {!loading && error && <ErrorState message={error} />}
          {!loading && !error && candidates.length === 0 && <EmptyState />}
          {!loading && !error && candidates.map((c) => (
            <CandidateCard
              key={c.id}
              candidate={c}
              selected={selectedId === c.id}
              onClick={() => setSelectedId(c.id)}
            />
          ))}
        </div>
      </main>

      {/* Right — detail panel */}
      <aside className="w-96 shrink-0 bg-white overflow-hidden">
        <CandidateDetailPanel candidateId={selectedId} />
      </aside>
    </div>
  );
}

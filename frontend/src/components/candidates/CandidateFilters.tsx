import type { CandidateFilters } from "../../features/candidates/types";

interface Props {
  filters: CandidateFilters;
  onChange: (filters: CandidateFilters) => void;
}

export function CandidateFiltersPanel({ filters, onChange }: Props) {
  function set(key: keyof CandidateFilters, value: string) {
    onChange({ ...filters, [key]: value });
  }

  return (
    <div className="space-y-3">
      <div>
        <label className="block text-xs font-medium text-gray-600 mb-1">Language</label>
        <input
          type="text"
          placeholder="e.g. Python"
          value={filters.language}
          onChange={(e) => set("language", e.target.value)}
          className="w-full text-sm border border-gray-200 rounded-md px-3 py-1.5 focus:outline-none focus:ring-2 focus:ring-blue-400"
        />
      </div>

      <div>
        <label className="block text-xs font-medium text-gray-600 mb-1">Location</label>
        <input
          type="text"
          placeholder="e.g. San Francisco"
          value={filters.location}
          onChange={(e) => set("location", e.target.value)}
          className="w-full text-sm border border-gray-200 rounded-md px-3 py-1.5 focus:outline-none focus:ring-2 focus:ring-blue-400"
        />
      </div>

      <div className="flex gap-2">
        <div className="flex-1">
          <label className="block text-xs font-medium text-gray-600 mb-1">Min followers</label>
          <input
            type="number"
            min={0}
            placeholder="0"
            value={filters.min_followers}
            onChange={(e) => set("min_followers", e.target.value)}
            className="w-full text-sm border border-gray-200 rounded-md px-3 py-1.5 focus:outline-none focus:ring-2 focus:ring-blue-400"
          />
        </div>
        <div className="flex-1">
          <label className="block text-xs font-medium text-gray-600 mb-1">Min repos</label>
          <input
            type="number"
            min={0}
            placeholder="0"
            value={filters.min_repos}
            onChange={(e) => set("min_repos", e.target.value)}
            className="w-full text-sm border border-gray-200 rounded-md px-3 py-1.5 focus:outline-none focus:ring-2 focus:ring-blue-400"
          />
        </div>
      </div>

      <div>
        <label className="block text-xs font-medium text-gray-600 mb-1">Profile completeness</label>
        <select
          value={filters.profile_completeness}
          onChange={(e) => set("profile_completeness", e.target.value)}
          className="w-full text-sm border border-gray-200 rounded-md px-3 py-1.5 focus:outline-none focus:ring-2 focus:ring-blue-400"
        >
          <option value="">Any</option>
          <option value="high">High</option>
          <option value="medium">Medium</option>
          <option value="low">Low</option>
        </select>
      </div>

      <button
        onClick={() =>
          onChange({ q: "", language: "", location: "", min_followers: "", max_followers: "", min_repos: "", profile_completeness: "" })
        }
        className="w-full text-xs text-gray-500 hover:text-gray-700 underline text-left"
      >
        Clear filters
      </button>
    </div>
  );
}

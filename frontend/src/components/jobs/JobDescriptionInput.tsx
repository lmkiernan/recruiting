interface Props {
  value: string;
  onChange: (value: string) => void;
  onEvaluate: () => void;
  onClear: () => void;
  evaluating: boolean;
  hasResults: boolean;
}

export function JobDescriptionInput({
  value,
  onChange,
  onEvaluate,
  onClear,
  evaluating,
  hasResults,
}: Props) {
  return (
    <div className="space-y-2">
      <label className="block text-xs font-semibold text-gray-700 uppercase tracking-wide">
        Job Description
      </label>
      <textarea
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder="Paste a job description to rank and score candidates against this role…"
        rows={6}
        className="w-full text-sm border border-gray-200 rounded-lg px-3 py-2 resize-none focus:outline-none focus:ring-2 focus:ring-blue-400 placeholder:text-gray-300"
      />
      <button
        onClick={onEvaluate}
        disabled={!value.trim() || evaluating}
        className="w-full py-2 px-3 rounded-lg text-sm font-medium bg-blue-600 text-white hover:bg-blue-700 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
      >
        {evaluating ? "Evaluating…" : "Evaluate Candidates"}
      </button>
      {hasResults && (
        <button
          onClick={onClear}
          className="w-full py-1.5 text-xs text-gray-400 hover:text-gray-600 underline"
        >
          Clear evaluation — browse all candidates
        </button>
      )}
    </div>
  );
}

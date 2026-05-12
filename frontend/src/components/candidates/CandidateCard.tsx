import { useShortlist } from "../../features/shortlists/ShortlistContext";
import type { CandidateSummary } from "../../features/candidates/types";
import { scoreBadgeColor } from "../../utils/scoreColor";

interface Props {
  candidate: CandidateSummary;
  selected: boolean;
  onClick: () => void;
  score?: number | null;
  aiScored?: boolean;
}

function ScoreBadge({ score }: { score: number }) {
  return (
    <span className={`shrink-0 text-xs font-semibold px-2 py-0.5 rounded-full ${scoreBadgeColor(score)}`}>
      {Math.round(score)}
    </span>
  );
}

function BookmarkButton({ candidate }: { candidate: CandidateSummary }) {
  const { isSaved, toggle } = useShortlist();
  const saved = isSaved(candidate.id);

  return (
    <button
      onClick={(e) => { e.stopPropagation(); toggle(candidate.id, saved ? undefined : candidate); }}
      title={saved ? "Remove from shortlist" : "Save to shortlist"}
      className="shrink-0 p-1 rounded hover:bg-gray-100 transition-colors"
    >
      {saved ? (
        <svg className="w-4 h-4 text-blue-500" fill="currentColor" viewBox="0 0 20 20">
          <path d="M5 4a2 2 0 012-2h6a2 2 0 012 2v14l-5-2.5L5 18V4z" />
        </svg>
      ) : (
        <svg className="w-4 h-4 text-gray-300" fill="none" stroke="currentColor" strokeWidth={1.5} viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" d="M17.593 3.322c1.1.128 1.907 1.077 1.907 2.185V21L12 17.25 4.5 21V5.507c0-1.108.806-2.057 1.907-2.185a48.507 48.507 0 0111.186 0z" />
        </svg>
      )}
    </button>
  );
}

export function CandidateCard({ candidate, selected, onClick, score, aiScored }: Props) {
  const displayName = candidate.name ?? candidate.github_username;

  return (
    <div
      role="button"
      tabIndex={0}
      onClick={onClick}
      onKeyDown={(e) => (e.key === "Enter" || e.key === " ") && onClick()}
      className={`w-full text-left p-4 rounded-lg border transition-colors cursor-pointer ${
        selected
          ? "border-blue-500 bg-blue-50"
          : "border-gray-200 bg-white hover:border-gray-300 hover:bg-gray-50"
      }`}
    >
      <div className="flex items-center gap-3">
        {candidate.avatar_url && (
          <img
            src={candidate.avatar_url}
            alt={displayName}
            className="w-10 h-10 rounded-full shrink-0"
          />
        )}
        <div className="min-w-0 flex-1">
          <p className="font-medium text-gray-900 truncate">{displayName}</p>
          <p className="text-sm text-gray-500 truncate">@{candidate.github_username}</p>
        </div>
        <div className="flex items-center gap-1 shrink-0">
          {score != null && (
            <>
              {aiScored && (
                <span className="text-xs font-medium px-1.5 py-0.5 rounded bg-purple-100 text-purple-600">
                  AI
                </span>
              )}
              <ScoreBadge score={score} />
            </>
          )}
          <BookmarkButton candidate={candidate} />
        </div>
      </div>

      {candidate.bio && (
        <p className="mt-2 text-sm text-gray-600 line-clamp-2">{candidate.bio}</p>
      )}

      <div className="mt-3 flex flex-wrap gap-1">
        {candidate.top_languages.slice(0, 4).map((l) => (
          <span key={l.language} className="px-2 py-0.5 text-xs rounded-full bg-gray-100 text-gray-700">
            {l.language}
          </span>
        ))}
      </div>

      <div className="mt-3 flex gap-4 text-xs text-gray-500">
        <span>{candidate.followers.toLocaleString()} followers</span>
        <span>{candidate.public_repos} repos</span>
        {candidate.location && <span>{candidate.location}</span>}
      </div>
    </div>
  );
}

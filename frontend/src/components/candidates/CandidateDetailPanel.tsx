import { useCandidateDetail } from "../../features/candidates/hooks";
import type { CandidateEvaluation, ScoreBreakdownItem } from "../../features/evaluations/types";
import { scoreBarColor, scoreTextColor } from "../../utils/scoreColor";
import { ErrorState } from "../ui/ErrorState";
import { Spinner } from "../ui/Spinner";

interface Props {
  candidateId: number | null;
  evaluation?: CandidateEvaluation | null;
}

function BreakdownBar({ item }: { item: ScoreBreakdownItem }) {
  const pct = Math.round((item.score / item.max) * 100);
  return (
    <div className="flex items-center gap-2 text-xs">
      <span className="w-32 shrink-0 text-gray-600">{item.label}</span>
      <div className="flex-1 h-1.5 bg-gray-100 rounded-full overflow-hidden">
        <div className={`h-full rounded-full ${scoreBarColor(pct)}`} style={{ width: `${pct}%` }} />
      </div>
      <span className="w-10 text-right text-gray-500 shrink-0">
        {item.score}/{item.max}
      </span>
    </div>
  );
}

function EvalSection({ evaluation }: { evaluation: CandidateEvaluation }) {
  const score = evaluation.final_score ?? 0;

  return (
    <div className="rounded-xl border border-gray-200 p-4 space-y-4 bg-gray-50">
      {/* Score header */}
      <div className="flex items-baseline justify-between">
        <div>
          <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide">Preliminary Match</p>
          {evaluation.summary && (
            <p className="text-xs text-gray-500 mt-0.5">{evaluation.summary}</p>
          )}
        </div>
        <span className={`text-2xl font-bold ${scoreTextColor(score)}`}>
          {Math.round(score)}<span className="text-sm font-normal text-gray-400">/100</span>
        </span>
      </div>

      {/* Breakdown bars */}
      {evaluation.breakdown.length > 0 && (
        <div className="space-y-2">
          {evaluation.breakdown.map((item) => (
            <BreakdownBar key={item.label} item={item} />
          ))}
        </div>
      )}

      {/* Evidence */}
      {evaluation.evidence.length > 0 && (
        <div>
          <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1.5">Evidence</p>
          <ul className="space-y-1">
            {evaluation.evidence.map((e, i) => (
              <li key={i} className="flex gap-2 text-xs text-gray-600">
                <span className="text-green-500 shrink-0 mt-px">✓</span>
                {e}
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Concerns */}
      {evaluation.concerns.length > 0 && (
        <div>
          <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1.5">Concerns</p>
          <ul className="space-y-1">
            {evaluation.concerns.map((c, i) => (
              <li key={i} className="flex gap-2 text-xs text-gray-600">
                <span className="text-amber-400 shrink-0 mt-px">!</span>
                {c}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

export function CandidateDetailPanel({ candidateId, evaluation }: Props) {
  const { candidate, loading, error } = useCandidateDetail(candidateId);

  if (candidateId === null) {
    return (
      <div className="flex items-center justify-center h-full text-gray-400 text-sm">
        Select a candidate to see details
      </div>
    );
  }

  if (loading) return <Spinner />;
  if (error) return <ErrorState message={error} />;
  if (!candidate) return null;

  const displayName = candidate.name ?? candidate.github_username;

  return (
    <div className="p-5 space-y-5 overflow-y-auto h-full">
      {/* Score section — only in eval mode */}
      {evaluation && <EvalSection evaluation={evaluation} />}

      {/* Header */}
      <div className="flex items-start gap-4">
        {candidate.avatar_url && (
          <img src={candidate.avatar_url} alt={displayName} className="w-14 h-14 rounded-full shrink-0" />
        )}
        <div className="min-w-0">
          <h2 className="text-lg font-semibold text-gray-900 truncate">{displayName}</h2>
          <a
            href={candidate.profile_url ?? `https://github.com/${candidate.github_username}`}
            target="_blank"
            rel="noreferrer"
            className="text-sm text-blue-500 hover:underline"
          >
            @{candidate.github_username}
          </a>
          {candidate.company && <p className="text-sm text-gray-500 mt-0.5">{candidate.company}</p>}
          {candidate.location && <p className="text-sm text-gray-500">{candidate.location}</p>}
        </div>
      </div>

      {/* Bio */}
      {candidate.bio && <p className="text-sm text-gray-700">{candidate.bio}</p>}

      {/* Stats */}
      <div className="flex gap-6 text-sm text-gray-600">
        <div><span className="font-medium text-gray-900">{candidate.followers.toLocaleString()}</span> followers</div>
        <div><span className="font-medium text-gray-900">{candidate.public_repos}</span> repos</div>
        <div><span className="font-medium text-gray-900">{candidate.following}</span> following</div>
      </div>

      {/* Languages */}
      {candidate.languages.length > 0 && (
        <div>
          <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">Languages</h3>
          <div className="flex flex-wrap gap-1.5">
            {candidate.languages
              .sort((a, b) => b.repo_count - a.repo_count)
              .map((l) => (
                <span key={l.language} className="px-2.5 py-1 text-xs rounded-full bg-blue-50 text-blue-700 border border-blue-100">
                  {l.language} <span className="opacity-60">×{l.repo_count}</span>
                </span>
              ))}
          </div>
        </div>
      )}

      {/* Top Repos */}
      {candidate.repositories.length > 0 && (
        <div>
          <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">Top repositories</h3>
          <div className="space-y-2">
            {candidate.repositories.map((repo) => (
              <a
                key={repo.id}
                href={repo.url ?? "#"}
                target="_blank"
                rel="noreferrer"
                className="block p-3 rounded-lg border border-gray-100 hover:border-gray-200 hover:bg-gray-50 transition-colors"
              >
                <div className="flex items-center justify-between gap-2">
                  <span className="text-sm font-medium text-blue-600 truncate">{repo.name}</span>
                  <div className="flex gap-2 text-xs text-gray-400 shrink-0">
                    <span>★ {repo.stars}</span>
                    <span>⑂ {repo.forks}</span>
                  </div>
                </div>
                {repo.description && (
                  <p className="mt-1 text-xs text-gray-500 line-clamp-2">{repo.description}</p>
                )}
                {repo.language && (
                  <span className="mt-1.5 inline-block text-xs text-gray-400">{repo.language}</span>
                )}
              </a>
            ))}
          </div>
        </div>
      )}

      {/* Profile completeness */}
      <div className="pt-2 border-t border-gray-100">
        <span className={`inline-block text-xs px-2 py-0.5 rounded-full font-medium ${
          candidate.profile_completeness === "high"
            ? "bg-green-50 text-green-700"
            : candidate.profile_completeness === "medium"
            ? "bg-yellow-50 text-yellow-700"
            : "bg-gray-100 text-gray-500"
        }`}>
          {candidate.profile_completeness} profile completeness
        </span>
      </div>
    </div>
  );
}

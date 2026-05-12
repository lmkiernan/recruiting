export function scoreBadgeColor(score: number): string {
  return score >= 70
    ? "bg-green-100 text-green-700"
    : score >= 45
    ? "bg-yellow-100 text-yellow-700"
    : "bg-gray-100 text-gray-500";
}

export function scoreTextColor(score: number): string {
  return score >= 70 ? "text-green-600" : score >= 45 ? "text-yellow-600" : "text-gray-500";
}

export function scoreBarColor(pct: number): string {
  return pct >= 70 ? "bg-green-400" : pct >= 45 ? "bg-yellow-400" : "bg-gray-300";
}

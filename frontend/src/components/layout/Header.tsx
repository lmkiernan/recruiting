import { useShortlist } from "../../features/shortlists/ShortlistContext";

export function Header() {
  const { count } = useShortlist();

  return (
    <header className="flex items-center justify-between px-5 py-2.5 bg-white border-b border-gray-200 shrink-0">
      <span className="text-sm font-semibold text-gray-900">Recruiter Signal</span>
      {count > 0 && (
        <span className="text-xs text-gray-500">
          <span className="font-medium text-blue-600">{count}</span> shortlisted
        </span>
      )}
    </header>
  );
}

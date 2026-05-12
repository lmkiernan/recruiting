import { createContext, useCallback, useContext, useState } from "react";
import type { CandidateSummary } from "../candidates/types";

const STORAGE_KEY = "shortlist";

interface StoredShortlist {
  ids: number[];
  cache: Record<number, CandidateSummary>;
}

function load(): StoredShortlist {
  try {
    return JSON.parse(localStorage.getItem(STORAGE_KEY) ?? "null") ?? { ids: [], cache: {} };
  } catch {
    return { ids: [], cache: {} };
  }
}

interface ShortlistState {
  savedIds: number[];
  candidateCache: Record<number, CandidateSummary>;
  toggle: (candidateId: number, candidate?: CandidateSummary) => void;
  isSaved: (candidateId: number) => boolean;
  count: number;
}

const ShortlistContext = createContext<ShortlistState>({
  savedIds: [],
  candidateCache: {},
  toggle: () => {},
  isSaved: () => false,
  count: 0,
});

export function ShortlistProvider({ children }: { children: React.ReactNode }) {
  const [shortlist, setShortlist] = useState<StoredShortlist>(load);

  const toggle = useCallback((candidateId: number, candidate?: CandidateSummary) => {
    setShortlist((prev) => {
      const removing = prev.ids.includes(candidateId);
      const nextIds = removing
        ? prev.ids.filter((id) => id !== candidateId)
        : [...prev.ids, candidateId];
      const nextCache = { ...prev.cache };
      if (removing) {
        delete nextCache[candidateId];
      } else if (candidate) {
        nextCache[candidateId] = candidate;
      }
      const next = { ids: nextIds, cache: nextCache };
      localStorage.setItem(STORAGE_KEY, JSON.stringify(next));
      return next;
    });
  }, []);

  const isSaved = useCallback(
    (candidateId: number) => shortlist.ids.includes(candidateId),
    [shortlist.ids],
  );

  return (
    <ShortlistContext.Provider value={{
      savedIds: shortlist.ids,
      candidateCache: shortlist.cache,
      toggle,
      isSaved,
      count: shortlist.ids.length,
    }}>
      {children}
    </ShortlistContext.Provider>
  );
}

export const useShortlist = () => useContext(ShortlistContext);

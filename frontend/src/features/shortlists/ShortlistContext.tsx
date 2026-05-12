import { createContext, useCallback, useContext, useState } from "react";

const STORAGE_KEY = "shortlisted_candidates";

function loadSaved(): number[] {
  try {
    return JSON.parse(localStorage.getItem(STORAGE_KEY) ?? "[]");
  } catch {
    return [];
  }
}

interface ShortlistState {
  savedIds: number[];
  toggle: (candidateId: number) => void;
  isSaved: (candidateId: number) => boolean;
  count: number;
}

const ShortlistContext = createContext<ShortlistState>({
  savedIds: [],
  toggle: () => {},
  isSaved: () => false,
  count: 0,
});

export function ShortlistProvider({ children }: { children: React.ReactNode }) {
  const [savedIds, setSavedIds] = useState<number[]>(loadSaved);

  const toggle = useCallback((candidateId: number) => {
    setSavedIds((prev) => {
      const next = prev.includes(candidateId)
        ? prev.filter((id) => id !== candidateId)
        : [...prev, candidateId];
      localStorage.setItem(STORAGE_KEY, JSON.stringify(next));
      return next;
    });
  }, []);

  const isSaved = useCallback(
    (candidateId: number) => savedIds.includes(candidateId),
    [savedIds],
  );

  return (
    <ShortlistContext.Provider value={{ savedIds, toggle, isSaved, count: savedIds.length }}>
      {children}
    </ShortlistContext.Provider>
  );
}

export const useShortlist = () => useContext(ShortlistContext);

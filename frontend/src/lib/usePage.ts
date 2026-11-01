import { useCallback, useState } from "react";

/**
 * Page number for a filtered list. Changing any filter (the `resetKey`)
 * returns to page 1 in the same render, so the list never requests a page
 * that belongs to the previous filters.
 */
export function usePage(resetKey: string) {
  const [state, setState] = useState({ page: 1, key: resetKey });
  const page = state.key === resetKey ? state.page : 1;
  const setPage = useCallback(
    (next: number) => setState({ page: next, key: resetKey }),
    [resetKey],
  );
  return [page, setPage] as const;
}

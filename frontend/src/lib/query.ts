/** Query-string helpers and mutation helper shared by the API hooks. */

import { useMutation } from "@tanstack/react-query";

export type QueryParams = Record<
  string,
  string | number | boolean | null | undefined
>;

export function toQueryString(params: QueryParams): string {
  const search = new URLSearchParams();

  for (const [key, value] of Object.entries(params)) {
    if (value === undefined || value === null || value === "") continue;
    search.set(key, String(value));
  }

  const query = search.toString();
  return query ? `?${query}` : "";
}

/** Default page size for every paginated list. */
export const PAGE_SIZE = 20;

/** A mutation that runs `invalidate` once it succeeds. */
export function useInvalidatingMutation<TData, TVariables>(
  mutationFn: (variables: TVariables) => Promise<TData>,
  invalidate: () => unknown,
) {
  return useMutation({
    mutationFn,
    onSuccess: () => {
      void invalidate();
    },
  });
}

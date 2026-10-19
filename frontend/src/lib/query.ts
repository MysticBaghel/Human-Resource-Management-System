/** Query-string helpers shared by the list hooks. */

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

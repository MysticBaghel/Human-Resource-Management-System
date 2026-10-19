/** Shapes shared by more than one endpoint. */

/** The project-wide page-number pagination envelope. */
export type Paginated<T> = {
  count: number;
  page: number;
  pages: number;
  page_size: number;
  results: T[];
};

/** Date helpers for date-only values (no timezone drift). */

export function toIsoDate(date: Date): string {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

export function parseIsoDate(isoDate: string): Date {
  return new Date(`${isoDate}T00:00:00`);
}

export function formatLongDate(isoDate: string): string {
  return parseIsoDate(isoDate).toLocaleDateString(undefined, {
    day: "numeric",
    month: "short",
    year: "numeric",
  });
}

export function formatDateRange(start: string, end: string): string {
  if (start === end) return formatLongDate(start);

  const startDate = parseIsoDate(start);
  const endDate = parseIsoDate(end);
  const sameMonth =
    startDate.getMonth() === endDate.getMonth() &&
    startDate.getFullYear() === endDate.getFullYear();

  if (sameMonth) {
    return `${startDate.getDate()}–${formatLongDate(end)}`;
  }
  return `${startDate.toLocaleDateString(undefined, {
    day: "numeric",
    month: "short",
  })} – ${formatLongDate(end)}`;
}

export function monthLabel(year: number, month: number): string {
  return new Date(year, month - 1, 1).toLocaleDateString(undefined, {
    month: "long",
    year: "numeric",
  });
}

export function shiftMonth(
  year: number,
  month: number,
  delta: number,
): { year: number; month: number } {
  const date = new Date(year, month - 1 + delta, 1);
  return { year: date.getFullYear(), month: date.getMonth() + 1 };
}

/** Monday-first grid for one month, padded with nulls. */
export function monthGrid(year: number, month: number): (Date | null)[][] {
  const first = new Date(year, month - 1, 1);
  const daysInMonth = new Date(year, month, 0).getDate();
  const leading = (first.getDay() + 6) % 7; // Monday = 0

  const cells: (Date | null)[] = Array.from({ length: leading }, () => null);
  for (let day = 1; day <= daysInMonth; day += 1) {
    cells.push(new Date(year, month - 1, day));
  }
  while (cells.length % 7 !== 0) cells.push(null);

  const weeks: (Date | null)[][] = [];
  for (let index = 0; index < cells.length; index += 7) {
    weeks.push(cells.slice(index, index + 7));
  }
  return weeks;
}

/** ISO dates between two inclusive ISO dates. */
export function eachDate(start: string, end: string): string[] {
  const dates: string[] = [];
  const current = parseIsoDate(start);
  const last = parseIsoDate(end);
  while (current <= last) {
    dates.push(toIsoDate(current));
    current.setDate(current.getDate() + 1);
  }
  return dates;
}

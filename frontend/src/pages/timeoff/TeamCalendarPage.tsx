/** Team calendar: one month of approved leave, scoped by the API. */

import { ChevronLeft, ChevronRight } from "lucide-react";
import { useState } from "react";

import {
  type CalendarLeave,
  useCalendar,
  useLeaveTypes,
} from "@/api/leave";
import { ErrorState } from "@/components/common/states";
import {
  leaveChipClass,
  leaveDotClass,
} from "@/components/leave/leaveColors";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import {
  eachDate,
  monthGrid,
  monthLabel,
  shiftMonth,
  toIsoDate,
} from "@/lib/date";
import { cn } from "@/lib/utils";

const WEEKDAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];

export function TeamCalendarPage() {
  const now = new Date();
  const [cursor, setCursor] = useState({
    year: now.getFullYear(),
    month: now.getMonth() + 1,
  });

  const { data, isLoading, isError, error, refetch } = useCalendar(
    cursor.year,
    cursor.month,
  );
  const { data: typesData } = useLeaveTypes();
  const weeks = monthGrid(cursor.year, cursor.month);

  const byDay = new Map<string, CalendarLeave[]>();
  for (const entry of data?.results ?? []) {
    for (const day of eachDate(entry.start_date, entry.end_date)) {
      const list = byDay.get(day) ?? [];
      list.push(entry);
      byDay.set(day, list);
    }
  }
  const holidayByDay = new Map(
    (data?.holidays ?? []).map((holiday) => [holiday.date, holiday.name]),
  );

  function goToToday() {
    const today = new Date();
    setCursor({ year: today.getFullYear(), month: today.getMonth() + 1 });
  }

  return (
    <div className="mx-auto w-full max-w-5xl space-y-6">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div className="space-y-1">
          <h1 className="text-2xl font-semibold tracking-tight">
            Team calendar
          </h1>
          <p className="text-sm text-muted-foreground">
            Approved leave for the people you can see.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <Button
            type="button"
            variant="outline"
            size="icon"
            aria-label="Previous month"
            onClick={() => setCursor(shiftMonth(cursor.year, cursor.month, -1))}
          >
            <ChevronLeft className="h-4 w-4" aria-hidden="true" />
          </Button>
          <Button type="button" variant="outline" size="sm" onClick={goToToday}>
            Today
          </Button>
          <Button
            type="button"
            variant="outline"
            size="icon"
            aria-label="Next month"
            onClick={() => setCursor(shiftMonth(cursor.year, cursor.month, 1))}
          >
            <ChevronRight className="h-4 w-4" aria-hidden="true" />
          </Button>
          <span className="min-w-[130px] text-sm font-medium">
            {monthLabel(cursor.year, cursor.month)}
          </span>
        </div>
      </div>

      <Card>
        <CardContent className="space-y-4 p-3 sm:p-6">
          {isLoading ? (
            <Skeleton className="h-96 w-full" />
          ) : isError ? (
            <ErrorState
              title="Could not load the calendar"
              message={error instanceof Error ? error.message : undefined}
              onRetry={() => void refetch()}
            />
          ) : (
            <>
              <div className="grid grid-cols-7 overflow-hidden rounded-lg border-l border-t">
                {WEEKDAYS.map((weekday) => (
                  <div
                    key={weekday}
                    className="border-b border-r bg-muted/50 p-1 text-center text-[10px] font-medium sm:p-2 sm:text-xs"
                  >
                    {weekday}
                  </div>
                ))}

                {weeks.flatMap((week, weekIndex) =>
                  week.map((day, dayIndex) => {
                    if (day === null) {
                      return (
                        <div
                          key={`empty-${weekIndex}-${dayIndex}`}
                          className="min-h-16 border-b border-r bg-muted/20 sm:min-h-24"
                        />
                      );
                    }

                    const iso = toIsoDate(day);
                    const entries = byDay.get(iso) ?? [];
                    const holiday = holidayByDay.get(iso);

                    return (
                      <div
                        key={iso}
                        className={cn(
                          "min-h-16 border-b border-r p-1 sm:min-h-24",
                          holiday && "bg-amber-50/70",
                        )}
                      >
                        <div className="flex items-center justify-between gap-1">
                          <span className="text-[10px] font-medium sm:text-xs">
                            {day.getDate()}
                          </span>
                          {entries.length > 0 ? (
                            <span className="text-[9px] text-muted-foreground sm:hidden">
                              {entries.length}
                            </span>
                          ) : null}
                        </div>

                        {holiday ? (
                          <p
                            className="truncate text-[9px] leading-tight text-amber-700 sm:text-[10px]"
                            title={holiday}
                          >
                            {holiday}
                          </p>
                        ) : null}

                        <div className="mt-1 space-y-0.5">
                          {entries.slice(0, 3).map((entry) => (
                            <span
                              key={`${iso}-${entry.id}`}
                              title={`${entry.employee_name} · ${entry.leave_type_name}`}
                              className={cn(
                                "block truncate rounded px-1 text-[9px] leading-tight sm:text-[10px]",
                                leaveChipClass(entry.leave_type),
                              )}
                            >
                              <span className="hidden sm:inline">
                                {entry.employee_name}
                              </span>
                              <span className="sm:hidden">
                                {entry.employee_name.split(" ")[0]}
                              </span>
                              {entry.half_day ? " ½" : ""}
                            </span>
                          ))}
                          {entries.length > 3 ? (
                            <span className="block text-[9px] text-muted-foreground">
                              +{entries.length - 3} more
                            </span>
                          ) : null}
                        </div>
                      </div>
                    );
                  }),
                )}
              </div>

              <div className="flex flex-wrap items-center gap-x-4 gap-y-2 text-xs text-muted-foreground">
                {(typesData?.results ?? []).map((type) => (
                  <span key={type.id} className="inline-flex items-center gap-1.5">
                    <span
                      className={cn("h-2.5 w-2.5 rounded-full", leaveDotClass(type.id))}
                      aria-hidden="true"
                    />
                    {type.name}
                  </span>
                ))}
                <span className="inline-flex items-center gap-1.5">
                  <span className="h-2.5 w-2.5 rounded-full bg-amber-400" aria-hidden="true" />
                  Holiday
                </span>
              </div>

              {data && data.results.length === 0 ? (
                <p className="text-sm text-muted-foreground">
                  No approved leave this month.
                </p>
              ) : null}
            </>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

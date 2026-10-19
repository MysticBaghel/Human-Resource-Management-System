/** Admin/HR time-off directory: employee names only, each linking to their page. */

import { ChevronRight, Search } from "lucide-react";
import { useState } from "react";
import { Link } from "react-router-dom";

import { useEmployees } from "@/api/employees";
import { EmptyState, ErrorState } from "@/components/common/states";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { useDebouncedValue } from "@/lib/useDebouncedValue";

function DirectorySkeleton() {
  return (
    <div className="space-y-2" aria-busy="true" aria-live="polite">
      {Array.from({ length: 5 }).map((_, index) => (
        <Skeleton key={index} className="h-10 w-full" />
      ))}
      <span className="sr-only">Loading employees…</span>
    </div>
  );
}

export function LeaveDirectory() {
  const [search, setSearch] = useState("");
  const debouncedSearch = useDebouncedValue(search);
  const { data, isLoading, isError, error, refetch } = useEmployees({
    search: debouncedSearch || undefined,
    status: "active",
    page_size: 100,
  });
  const employees = data?.results ?? [];

  return (
    <div className="mx-auto w-full max-w-3xl space-y-6">
      <div className="space-y-1">
        <h1 className="text-2xl font-semibold tracking-tight">My time off</h1>
        <p className="text-sm text-muted-foreground">
          Choose a person to see their leave balances and requests.
        </p>
      </div>

      <Card>
        <CardContent className="space-y-4 p-4 sm:p-6">
          <div className="relative">
            <Search
              className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground"
              aria-hidden="true"
            />
            <Input
              type="search"
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              placeholder="Search employees"
              aria-label="Search employees"
              className="pl-9"
            />
          </div>

          {isLoading ? (
            <DirectorySkeleton />
          ) : isError ? (
            <ErrorState
              title="Could not load employees"
              message={error instanceof Error ? error.message : undefined}
              onRetry={() => void refetch()}
            />
          ) : employees.length === 0 ? (
            <EmptyState
              title={
                debouncedSearch
                  ? "No employees match this search"
                  : "No active employees"
              }
              description={
                debouncedSearch
                  ? "Try a different name."
                  : "Add people from the Employees page first."
              }
            />
          ) : (
            <ul className="divide-y">
              {employees.map((employee) => (
                <li key={employee.id}>
                  <Link
                    to={`/time-off/employees/${employee.id}`}
                    className="flex items-center justify-between gap-3 py-3 text-sm font-medium transition-colors hover:text-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                  >
                    <span className="truncate">{employee.full_name}</span>
                    <ChevronRight
                      className="h-4 w-4 shrink-0 text-muted-foreground"
                      aria-hidden="true"
                    />
                  </Link>
                </li>
              ))}
            </ul>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

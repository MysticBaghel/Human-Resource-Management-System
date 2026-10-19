/** Audit log: who changed what, newest first, HR and admin only. */

import { Search } from "lucide-react";
import { useEffect, useState } from "react";

import {
  AUDIT_MODELS,
  type AuditAction,
  type AuditEntry,
  useAuditActors,
  useAuditLogs,
} from "@/api/audit";
import { Pagination } from "@/components/common/Pagination";
import { EmptyState, ErrorState } from "@/components/common/states";
import { AuditActionBadge } from "@/components/audit/AuditActionBadge";
import { AuditDetailDialog } from "@/components/audit/AuditDetailDialog";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { formatDateTime } from "@/lib/format";
import { useDebouncedValue } from "@/lib/useDebouncedValue";

const PAGE_SIZE = 20;

function ListSkeleton() {
  return (
    <div className="space-y-2" aria-busy="true" aria-live="polite">
      {Array.from({ length: 6 }).map((_, index) => (
        <Skeleton key={index} className="h-14 w-full" />
      ))}
      <span className="sr-only">Loading audit events…</span>
    </div>
  );
}

export function AuditLogPage() {
  const [action, setAction] = useState("");
  const [model, setModel] = useState("");
  const [actor, setActor] = useState("");
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(1);
  const [selected, setSelected] = useState<AuditEntry | null>(null);

  const debouncedSearch = useDebouncedValue(search);
  const { data: actors } = useAuditActors();

  useEffect(() => {
    setPage(1);
  }, [action, model, actor, dateFrom, dateTo, debouncedSearch]);

  const filters = {
    action: (action || undefined) as AuditAction | undefined,
    model: model || undefined,
    actor: actor ? Number(actor) : undefined,
    date_from: dateFrom || undefined,
    date_to: dateTo || undefined,
    search: debouncedSearch || undefined,
    page,
    page_size: PAGE_SIZE,
  };

  const { data, isLoading, isError, error, refetch } = useAuditLogs(filters);
  const entries = data?.results ?? [];
  const hasFilters = Boolean(
    action || model || actor || dateFrom || dateTo || debouncedSearch,
  );

  function clearFilters() {
    setAction("");
    setModel("");
    setActor("");
    setDateFrom("");
    setDateTo("");
    setSearch("");
    setPage(1);
  }

  return (
    <div className="mx-auto w-full max-w-6xl space-y-6">
      <div className="space-y-1">
        <h1 className="text-2xl font-semibold tracking-tight">Audit log</h1>
        <p className="text-sm text-muted-foreground">
          Every audited change in the company, newest first.
          {data ? ` ${data.count} event${data.count === 1 ? "" : "s"}.` : ""}
        </p>
      </div>

      <Card>
        <CardContent className="space-y-4 p-4 sm:p-6">
          <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-4">
            <div className="relative sm:col-span-2 lg:col-span-1">
              <Search
                className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground"
                aria-hidden="true"
              />
              <Input
                type="search"
                value={search}
                onChange={(event) => setSearch(event.target.value)}
                placeholder="Search record or actor"
                aria-label="Search the audit log"
                className="pl-9"
              />
            </div>

            <Select
              value={action}
              onChange={(event) => setAction(event.target.value)}
              aria-label="Filter by action"
            >
              <option value="">All actions</option>
              <option value="create">Create</option>
              <option value="update">Update</option>
              <option value="delete">Delete</option>
            </Select>

            <Select
              value={model}
              onChange={(event) => setModel(event.target.value)}
              aria-label="Filter by resource"
            >
              <option value="">All resources</option>
              {AUDIT_MODELS.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </Select>

            <Select
              value={actor}
              onChange={(event) => setActor(event.target.value)}
              aria-label="Filter by actor"
            >
              <option value="">All actors</option>
              {(actors ?? []).map((option) => (
                <option key={option.id} value={option.id}>
                  {option.email}
                </option>
              ))}
            </Select>

            <Input
              type="date"
              value={dateFrom}
              onChange={(event) => setDateFrom(event.target.value)}
              aria-label="From date"
            />
            <Input
              type="date"
              value={dateTo}
              onChange={(event) => setDateTo(event.target.value)}
              aria-label="To date"
            />

            <Button
              type="button"
              variant="outline"
              onClick={clearFilters}
              disabled={!hasFilters}
            >
              Clear filters
            </Button>
          </div>

          {isLoading ? (
            <ListSkeleton />
          ) : isError ? (
            <ErrorState
              title="Could not load the audit log"
              message={error instanceof Error ? error.message : undefined}
              onRetry={() => void refetch()}
            />
          ) : entries.length === 0 ? (
            <EmptyState
              title={
                hasFilters
                  ? "No audit events match these filters"
                  : "No audit events yet"
              }
              description={
                hasFilters
                  ? "Try a different action, resource, actor or date range."
                  : "Changes to employees, teams, leave types and leave requests will appear here."
              }
              action={
                hasFilters ? (
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    onClick={clearFilters}
                  >
                    Clear filters
                  </Button>
                ) : undefined
              }
            />
          ) : (
            <>
              <div className="hidden lg:block">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>When</TableHead>
                      <TableHead>Actor</TableHead>
                      <TableHead>Action</TableHead>
                      <TableHead>Resource</TableHead>
                      <TableHead>Record</TableHead>
                      <TableHead>Summary</TableHead>
                      <TableHead className="text-right">Details</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {entries.map((entry) => (
                      <TableRow key={entry.id}>
                        <TableCell className="whitespace-nowrap text-xs text-muted-foreground">
                          {formatDateTime(entry.created_at)}
                        </TableCell>
                        <TableCell className="text-sm">
                          {entry.actor_label}
                        </TableCell>
                        <TableCell>
                          <AuditActionBadge
                            action={entry.action}
                            label={entry.action_label}
                          />
                        </TableCell>
                        <TableCell>
                          <Badge variant="outline">{entry.model_label}</Badge>
                        </TableCell>
                        <TableCell className="font-mono text-xs">
                          #{entry.object_id}
                        </TableCell>
                        <TableCell>
                          <button
                            type="button"
                            onClick={() => setSelected(entry)}
                            className="text-left text-sm font-medium hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                          >
                            {entry.summary}
                          </button>
                        </TableCell>
                        <TableCell className="text-right">
                          <Button
                            type="button"
                            variant="ghost"
                            size="sm"
                            onClick={() => setSelected(entry)}
                          >
                            View
                          </Button>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>

              <ul className="space-y-2 lg:hidden">
                {entries.map((entry) => (
                  <li key={entry.id} className="space-y-2 rounded-lg border p-3">
                    <div className="flex items-start justify-between gap-2">
                      <button
                        type="button"
                        onClick={() => setSelected(entry)}
                        className="min-w-0 text-left text-sm font-medium hover:underline"
                      >
                        {entry.summary}
                      </button>
                      <AuditActionBadge
                        action={entry.action}
                        label={entry.action_label}
                      />
                    </div>
                    <p className="text-xs text-muted-foreground">
                      {entry.model_label} #{entry.object_id} ·{" "}
                      {entry.actor_label}
                    </p>
                    <p className="text-xs text-muted-foreground">
                      {formatDateTime(entry.created_at)}
                    </p>
                    <Button
                      type="button"
                      variant="outline"
                      size="sm"
                      onClick={() => setSelected(entry)}
                    >
                      View changes
                    </Button>
                  </li>
                ))}
              </ul>

              <Pagination
                page={data?.page ?? page}
                pages={data?.pages ?? 1}
                count={data?.count ?? entries.length}
                pageSize={data?.page_size ?? PAGE_SIZE}
                onPageChange={setPage}
              />
            </>
          )}
        </CardContent>
      </Card>

      <AuditDetailDialog
        entry={selected}
        onClose={() => setSelected(null)}
      />
    </div>
  );
}

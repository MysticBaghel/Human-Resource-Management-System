/** HR/admin salary structures: current values, create, revise and history. */

import { History, Pencil, Plus, Search } from "lucide-react";
import { useState } from "react";

import { useEmployees } from "@/api/employees";
import { useSalaryStructures, type SalaryStructure } from "@/api/payroll";
import { Pagination } from "@/components/common/Pagination";
import { EmptyState, ErrorState, SkeletonRows } from "@/components/common/states";
import { SalaryRevisionDialog } from "@/components/payroll/SalaryRevisionDialog";
import { SalaryStructureDialog } from "@/components/payroll/SalaryStructureDialog";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { useDebouncedValue } from "@/lib/useDebouncedValue";
import { formatDate, formatMoney } from "@/lib/format";
import { errorMessage } from "@/lib/errors";
import { PAGE_SIZE } from "@/lib/query";
import { usePage } from "@/lib/usePage";

function ListSkeleton() {
  return <SkeletonRows count={6} height="h-14" label="Loading salary structures…" />;
}

export function SalaryStructuresPage() {
  const [search, setSearch] = useState("");
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editing, setEditing] = useState<SalaryStructure | null>(null);
  const [historyFor, setHistoryFor] = useState<SalaryStructure | null>(null);

  const debouncedSearch = useDebouncedValue(search);

  const [page, setPage] = usePage(JSON.stringify([debouncedSearch]));

  const { data, isLoading, isError, error, refetch } = useSalaryStructures({
    active: true,
    search: debouncedSearch || undefined,
    page,
    page_size: PAGE_SIZE,
  });
  const { data: employees } = useEmployees({ page_size: 100 });
  const { data: allStructures } = useSalaryStructures({
    active: true,
    page_size: 100,
  });

  const rows = data?.results ?? [];
  const covered = new Set(
    (allStructures?.results ?? []).map((structure) => structure.employee),
  );
  const availableEmployees = (employees?.results ?? []).filter(
    (employee) => employee.status === "active" && !covered.has(employee.id),
  );

  function openCreate() {
    setEditing(null);
    setDialogOpen(true);
  }

  function openEdit(structure: SalaryStructure) {
    setEditing(structure);
    setDialogOpen(true);
  }

  return (
    <div className="mx-auto w-full max-w-6xl space-y-6">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div className="space-y-1">
          <h1 className="text-2xl font-semibold tracking-tight">
            Salary structures
          </h1>
          <p className="text-sm text-muted-foreground">
            Current earnings and deductions. Each revision keeps the previous
            version in history.
          </p>
        </div>
        <Button onClick={openCreate}>
          <Plus className="h-4 w-4" aria-hidden="true" />
          New salary structure
        </Button>
      </div>

      <Card>
        <CardContent className="space-y-4 p-4 sm:p-6">
          <div className="relative max-w-md">
            <Search
              className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground"
              aria-hidden="true"
            />
            <Input
              type="search"
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              placeholder="Search name, email, job title or team"
              aria-label="Search salary structures"
              className="pl-9"
            />
          </div>

          {isLoading ? (
            <ListSkeleton />
          ) : isError ? (
            <ErrorState
              title="Could not load salary structures"
              message={errorMessage(error)}
              onRetry={() => void refetch()}
            />
          ) : rows.length === 0 ? (
            <EmptyState
              title={
                debouncedSearch
                  ? "No salary structures match this search"
                  : "No salary structures yet"
              }
              description={
                debouncedSearch
                  ? "Try a different search."
                  : "Add a structure for each employee to make them eligible for payroll."
              }
              action={
                debouncedSearch ? (
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    onClick={() => setSearch("")}
                  >
                    Clear search
                  </Button>
                ) : (
                  <Button type="button" size="sm" onClick={openCreate}>
                    Create the first structure
                  </Button>
                )
              }
            />
          ) : (
            <>
              <div className="hidden lg:block">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Employee</TableHead>
                      <TableHead>Role / team</TableHead>
                      <TableHead className="text-right">Gross</TableHead>
                      <TableHead className="text-right">Deductions</TableHead>
                      <TableHead className="text-right">Net</TableHead>
                      <TableHead>Effective</TableHead>
                      <TableHead className="text-right">Actions</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {rows.map((structure) => (
                      <TableRow key={structure.id}>
                        <TableCell>
                          <p className="font-medium">{structure.employee_name}</p>
                          <p className="text-xs text-muted-foreground">
                            {structure.employee_code} · {structure.email}
                          </p>
                        </TableCell>
                        <TableCell>
                          <p>{structure.designation || "—"}</p>
                          <p className="text-xs text-muted-foreground">
                            {structure.department ?? "No team"}
                          </p>
                        </TableCell>
                        <TableCell className="text-right tabular-nums">
                          {formatMoney(structure.gross_salary)}
                        </TableCell>
                        <TableCell className="text-right tabular-nums">
                          {formatMoney(structure.total_deductions)}
                        </TableCell>
                        <TableCell className="text-right font-medium tabular-nums">
                          {formatMoney(structure.net_salary)}
                        </TableCell>
                        <TableCell>{formatDate(structure.effective_date)}</TableCell>
                        <TableCell>
                          <div className="flex justify-end gap-1">
                            <Button
                              type="button"
                              variant="ghost"
                              size="sm"
                              onClick={() => openEdit(structure)}
                            >
                              <Pencil className="h-4 w-4" aria-hidden="true" />
                              <span className="sr-only lg:not-sr-only">
                                Revise
                              </span>
                            </Button>
                            <Button
                              type="button"
                              variant="ghost"
                              size="sm"
                              onClick={() => setHistoryFor(structure)}
                            >
                              <History className="h-4 w-4" aria-hidden="true" />
                              <span className="sr-only lg:not-sr-only">
                                History
                              </span>
                            </Button>
                          </div>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>

              <ul className="space-y-3 lg:hidden">
                {rows.map((structure) => (
                  <li key={structure.id} className="space-y-3 rounded-lg border p-3">
                    <div className="flex items-start justify-between gap-2">
                      <div className="min-w-0">
                        <p className="truncate text-sm font-medium">
                          {structure.employee_name}
                        </p>
                        <p className="text-xs text-muted-foreground">
                          {structure.employee_code} ·{" "}
                          {structure.department ?? "No team"}
                        </p>
                      </div>
                      <p className="shrink-0 text-sm font-semibold tabular-nums">
                        {formatMoney(structure.net_salary)}
                      </p>
                    </div>
                    <p className="text-xs text-muted-foreground">
                      Gross {formatMoney(structure.gross_salary)} · deductions{" "}
                      {formatMoney(structure.total_deductions)} · effective{" "}
                      {formatDate(structure.effective_date)}
                    </p>
                    <div className="flex gap-2">
                      <Button
                        type="button"
                        variant="outline"
                        size="sm"
                        className="flex-1"
                        onClick={() => openEdit(structure)}
                      >
                        Revise
                      </Button>
                      <Button
                        type="button"
                        variant="outline"
                        size="sm"
                        className="flex-1"
                        onClick={() => setHistoryFor(structure)}
                      >
                        History
                      </Button>
                    </div>
                  </li>
                ))}
              </ul>

              <Pagination
                page={data?.page ?? page}
                pages={data?.pages ?? 1}
                count={data?.count ?? rows.length}
                pageSize={data?.page_size ?? PAGE_SIZE}
                onPageChange={setPage}
              />
            </>
          )}
        </CardContent>
      </Card>

      <SalaryStructureDialog
        open={dialogOpen}
        onOpenChange={(open) => {
          setDialogOpen(open);
          if (!open) setEditing(null);
        }}
        employees={editing ? [] : availableEmployees}
        structure={editing}
      />

      <SalaryRevisionDialog
        open={historyFor !== null}
        onOpenChange={(open) => {
          if (!open) setHistoryFor(null);
        }}
        employee={historyFor?.employee ?? null}
        employeeName={historyFor?.employee_name}
      />
    </div>
  );
}

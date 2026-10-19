/** Employees: searchable, filterable, paginated list for HR, admin and managers. */

import { Search, UserPlus } from "lucide-react";
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import {
  type EmployeeStatus,
  STATUS_LABELS,
  useEmployees,
} from "@/api/employees";
import { ROLE_LABELS, type Role } from "@/api/queries";
import { useTeams } from "@/api/teams";
import { useAuth } from "@/auth/AuthContext";
import { Pagination } from "@/components/common/Pagination";
import { EmptyState, ErrorState } from "@/components/common/states";
import { StatusBadge } from "@/components/employees/StatusBadge";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
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
import { useDebouncedValue } from "@/lib/useDebouncedValue";

const ROLE_OPTIONS: Role[] = ["admin", "hr", "manager", "employee"];
const STATUS_OPTIONS: EmployeeStatus[] = ["active", "inactive"];

const PAGE_SIZE = 20;

function ListSkeleton() {
  return (
    <div className="space-y-2" aria-busy="true" aria-live="polite">
      {Array.from({ length: 6 }).map((_, index) => (
        <Skeleton key={index} className="h-14 w-full" />
      ))}
      <span className="sr-only">Loading employees…</span>
    </div>
  );
}

export function EmployeesPage() {
  const { hasRole } = useAuth();
  const canManage = hasRole("admin", "hr");

  const [search, setSearch] = useState("");
  const [team, setTeam] = useState("");
  const [status, setStatus] = useState("");
  const [role, setRole] = useState("");
  const [page, setPage] = useState(1);

  const debouncedSearch = useDebouncedValue(search);
  const { data: teams } = useTeams();

  useEffect(() => {
    setPage(1);
  }, [debouncedSearch, team, status, role]);

  const filters = {
    search: debouncedSearch || undefined,
    team: team ? Number(team) : undefined,
    status: (status || undefined) as EmployeeStatus | undefined,
    role: (role || undefined) as Role | undefined,
    page,
    page_size: PAGE_SIZE,
  };

  const { data, isLoading, isError, error, refetch } = useEmployees(filters);
  const hasFilters = Boolean(debouncedSearch || team || status || role);
  const rows = data?.results ?? [];

  function clearFilters() {
    setSearch("");
    setTeam("");
    setStatus("");
    setRole("");
    setPage(1);
  }

  return (
    <div className="mx-auto w-full max-w-6xl space-y-6">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div className="space-y-1">
          <h1 className="text-2xl font-semibold tracking-tight">Employees</h1>
          <p className="text-sm text-muted-foreground">
            {data ? `${data.count} ${data.count === 1 ? "person" : "people"}` : "Everyone in the company"}
            {hasRole("manager") && !canManage ? " in the teams you lead" : ""}
          </p>
        </div>
        {canManage ? (
          <Button asChild>
            <Link to="/employees/new">
              <UserPlus className="h-4 w-4" aria-hidden="true" />
              New employee
            </Link>
          </Button>
        ) : null}
      </div>

      <Card>
        <CardContent className="space-y-4 p-4 sm:p-6">
          <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-5">
            <div className="relative lg:col-span-2">
              <Search
                className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground"
                aria-hidden="true"
              />
              <Input
                type="search"
                value={search}
                onChange={(event) => setSearch(event.target.value)}
                placeholder="Search name, email or job title"
                aria-label="Search employees"
                className="pl-9"
              />
            </div>
            <Select
              value={team}
              onChange={(event) => setTeam(event.target.value)}
              aria-label="Filter by team"
            >
              <option value="">All teams</option>
              {teams?.results.map((option) => (
                <option key={option.id} value={option.id}>
                  {option.name}
                </option>
              ))}
            </Select>
            <Select
              value={status}
              onChange={(event) => setStatus(event.target.value)}
              aria-label="Filter by status"
            >
              <option value="">All statuses</option>
              {STATUS_OPTIONS.map((option) => (
                <option key={option} value={option}>
                  {STATUS_LABELS[option]}
                </option>
              ))}
            </Select>
            <Select
              value={role}
              onChange={(event) => setRole(event.target.value)}
              aria-label="Filter by role"
            >
              <option value="">All roles</option>
              {ROLE_OPTIONS.map((option) => (
                <option key={option} value={option}>
                  {ROLE_LABELS[option]}
                </option>
              ))}
            </Select>
          </div>

          {isLoading ? (
            <ListSkeleton />
          ) : isError ? (
            <ErrorState
              title="Could not load employees"
              message={error instanceof Error ? error.message : undefined}
              onRetry={() => void refetch()}
            />
          ) : rows.length === 0 ? (
            <EmptyState
              title={hasFilters ? "No employees match these filters" : "No employees yet"}
              description={
                hasFilters
                  ? "Try a different search or clear the filters."
                  : "New employees get an email inviting them to set a password."
              }
              action={
                hasFilters ? (
                  <Button type="button" variant="outline" size="sm" onClick={clearFilters}>
                    Clear filters
                  </Button>
                ) : canManage ? (
                  <Button asChild size="sm">
                    <Link to="/employees/new">Add the first employee</Link>
                  </Button>
                ) : undefined
              }
            />
          ) : (
            <>
              {/* Table from md up; cards below so 375px stays readable. */}
              <div className="hidden md:block">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Employee</TableHead>
                      <TableHead>Job title</TableHead>
                      <TableHead>Team</TableHead>
                      <TableHead>Role</TableHead>
                      <TableHead>Status</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {rows.map((employee) => (
                      <TableRow key={employee.id}>
                        <TableCell>
                          <Link
                            to={`/employees/${employee.id}`}
                            className="font-medium hover:underline"
                          >
                            {employee.full_name}
                          </Link>
                          <p className="text-xs text-muted-foreground">
                            {employee.email}
                          </p>
                        </TableCell>
                        <TableCell>{employee.job_title || "—"}</TableCell>
                        <TableCell>{employee.team_name ?? "—"}</TableCell>
                        <TableCell>
                          <Badge variant="outline">{ROLE_LABELS[employee.role]}</Badge>
                        </TableCell>
                        <TableCell>
                          <StatusBadge status={employee.status} />
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>

              <ul className="space-y-2 md:hidden">
                {rows.map((employee) => (
                  <li key={employee.id} className="rounded-lg border p-3">
                    <div className="flex items-start justify-between gap-2">
                      <div className="min-w-0">
                        <Link
                          to={`/employees/${employee.id}`}
                          className="block truncate text-sm font-medium hover:underline"
                        >
                          {employee.full_name}
                        </Link>
                        <p className="truncate text-xs text-muted-foreground">
                          {[employee.job_title, employee.team_name]
                            .filter(Boolean)
                            .join(" · ") || employee.email}
                        </p>
                      </div>
                      <StatusBadge status={employee.status} />
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
    </div>
  );
}

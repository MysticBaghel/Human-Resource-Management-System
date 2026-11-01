/** HR/admin client directory for invoicing. */

import { ArrowLeft, Pencil, Plus, Search, Trash2, Users } from "lucide-react";
import { useState } from "react";
import { Link } from "react-router-dom";

import {
  useClients,
  useDeleteClient,
  type Client,
} from "@/api/invoices";
import { ConfirmDialog } from "@/components/common/ConfirmDialog";
import { Pagination } from "@/components/common/Pagination";
import { EmptyState, ErrorState, SkeletonRows } from "@/components/common/states";
import { ClientDialog } from "@/components/invoices/ClientDialog";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { toast } from "@/components/ui/toast";
import { useDebouncedValue } from "@/lib/useDebouncedValue";
import { errorMessage, showError } from "@/lib/errors";
import { PAGE_SIZE } from "@/lib/query";
import { usePage } from "@/lib/usePage";

function ListSkeleton() {
  return <SkeletonRows count={5} height="h-16" label="Loading clients…" />;
}

export function ClientsPage() {
  const [search, setSearch] = useState("");
  const [active, setActive] = useState("");
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editing, setEditing] = useState<Client | null>(null);
  const [removeTarget, setRemoveTarget] = useState<Client | null>(null);
  const debouncedSearch = useDebouncedValue(search);
  const [page, setPage] = usePage(JSON.stringify([debouncedSearch, active]));
  const deleteMutation = useDeleteClient();

  const { data, isLoading, isError, error, refetch } = useClients({
    search: debouncedSearch || undefined,
    active: active === "" ? undefined : active === "true",
    page,
    page_size: PAGE_SIZE,
  });

  const rows = data?.results ?? [];
  const hasFilters = Boolean(debouncedSearch || active);

  async function handleDelete() {
    if (!removeTarget) return;
    try {
      await deleteMutation.mutateAsync(removeTarget.id);
      toast({
        title: "Client deleted",
        description: removeTarget.name,
        variant: "success",
      });
      setRemoveTarget(null);
    } catch (caught) {
      showError("Could not delete the client", caught);
    }
  }

  return (
    <div className="mx-auto w-full max-w-6xl space-y-6">
      <div className="space-y-2">
        <Button asChild variant="ghost" size="sm" className="px-0">
          <Link to="/invoices">
            <ArrowLeft className="h-4 w-4" aria-hidden="true" />
            All invoices
          </Link>
        </Button>
        <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
          <div className="space-y-1">
            <h1 className="text-2xl font-semibold tracking-tight">Clients</h1>
            <p className="text-sm text-muted-foreground">
              Companies and people you invoice. Billing details are copied onto
              each invoice.
            </p>
          </div>
          <Button
            type="button"
            onClick={() => {
              setEditing(null);
              setDialogOpen(true);
            }}
          >
            <Plus className="h-4 w-4" aria-hidden="true" />
            New client
          </Button>
        </div>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <Users className="h-4 w-4" aria-hidden="true" />
            Billing directory
          </CardTitle>
          <CardDescription>
            Deactivate a client to stop new invoices without losing history.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid gap-2 sm:grid-cols-[1fr_180px]">
            <div className="relative">
              <Search
                className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground"
                aria-hidden="true"
              />
              <Input
                type="search"
                value={search}
                onChange={(event) => setSearch(event.target.value)}
                placeholder="Search name, contact, email or tax id"
                aria-label="Search clients"
                className="pl-9"
              />
            </div>
            <Select
              value={active}
              onChange={(event) => setActive(event.target.value)}
              aria-label="Filter clients by status"
            >
              <option value="">All clients</option>
              <option value="true">Active only</option>
              <option value="false">Inactive only</option>
            </Select>
          </div>

          {isLoading ? (
            <ListSkeleton />
          ) : isError ? (
            <ErrorState
              title="Could not load clients"
              message={errorMessage(error)}
              onRetry={() => void refetch()}
            />
          ) : rows.length === 0 ? (
            <EmptyState
              title={hasFilters ? "No clients match this search" : "No clients yet"}
              description={
                hasFilters
                  ? "Try a different search or status."
                  : "Add a client so you can generate an invoice."
              }
              action={
                hasFilters ? (
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    onClick={() => {
                      setSearch("");
                      setActive("");
                    }}
                  >
                    Clear filters
                  </Button>
                ) : (
                  <Button
                    type="button"
                    size="sm"
                    onClick={() => setDialogOpen(true)}
                  >
                    Add the first client
                  </Button>
                )
              }
            />
          ) : (
            <>
              <div className="hidden md:block">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Client</TableHead>
                      <TableHead>Contact</TableHead>
                      <TableHead>Billing email</TableHead>
                      <TableHead className="text-right">Invoices</TableHead>
                      <TableHead>Status</TableHead>
                      <TableHead className="text-right">Actions</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {rows.map((client) => (
                      <TableRow key={client.id}>
                        <TableCell>
                          <p className="font-medium">{client.name}</p>
                          <p className="text-xs text-muted-foreground">
                            {client.code}
                            {client.tax_id ? ` · ${client.tax_id}` : ""}
                          </p>
                        </TableCell>
                        <TableCell>
                          {client.contact_name || "—"}
                          {client.phone ? (
                            <p className="text-xs text-muted-foreground">
                              {client.phone}
                            </p>
                          ) : null}
                        </TableCell>
                        <TableCell>{client.email || "—"}</TableCell>
                        <TableCell className="text-right tabular-nums">
                          {client.invoice_count}
                        </TableCell>
                        <TableCell>
                          <Badge variant={client.is_active ? "success" : "outline"}>
                            {client.is_active ? "Active" : "Inactive"}
                          </Badge>
                        </TableCell>
                        <TableCell>
                          <div className="flex justify-end gap-1">
                            <Button
                              type="button"
                              variant="ghost"
                              size="sm"
                              onClick={() => {
                                setEditing(client);
                                setDialogOpen(true);
                              }}
                            >
                              <Pencil className="h-4 w-4" aria-hidden="true" />
                              Edit
                            </Button>
                            <Button
                              type="button"
                              variant="ghost"
                              size="icon"
                              className="h-9 w-9 text-muted-foreground"
                              onClick={() => setRemoveTarget(client)}
                              disabled={client.invoice_count > 0}
                              aria-label={`Delete ${client.name}`}
                            >
                              <Trash2 className="h-4 w-4" aria-hidden="true" />
                            </Button>
                          </div>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>

              <ul className="space-y-3 md:hidden">
                {rows.map((client) => (
                  <li key={client.id} className="space-y-3 rounded-lg border p-3">
                    <div className="flex items-start justify-between gap-2">
                      <div className="min-w-0">
                        <p className="truncate text-sm font-medium">{client.name}</p>
                        <p className="text-xs text-muted-foreground">
                          {client.contact_name || "No contact"} ·{" "}
                          {client.email || "No email"}
                        </p>
                      </div>
                      <Badge variant={client.is_active ? "success" : "outline"}>
                        {client.is_active ? "Active" : "Inactive"}
                      </Badge>
                    </div>
                    <p className="text-xs text-muted-foreground">
                      {client.invoice_count} invoice
                      {client.invoice_count === 1 ? "" : "s"}
                      {client.tax_id ? ` · ${client.tax_id}` : ""}
                    </p>
                    <div className="flex gap-2">
                      <Button
                        type="button"
                        variant="outline"
                        size="sm"
                        className="flex-1"
                        onClick={() => {
                          setEditing(client);
                          setDialogOpen(true);
                        }}
                      >
                        Edit
                      </Button>
                      <Button
                        type="button"
                        variant="outline"
                        size="sm"
                        className="flex-1"
                        onClick={() => setRemoveTarget(client)}
                        disabled={client.invoice_count > 0}
                      >
                        Delete
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

      <ClientDialog
        open={dialogOpen}
        onOpenChange={(open) => {
          setDialogOpen(open);
          if (!open) setEditing(null);
        }}
        client={editing}
      />

      <ConfirmDialog
        open={removeTarget !== null}
        onOpenChange={(open) => {
          if (!open) setRemoveTarget(null);
        }}
        title="Delete this client?"
        description={removeTarget?.name}
        cancelLabel="Keep client"
        confirmLabel="Delete client"
        pendingLabel="Deleting…"
        isPending={deleteMutation.isPending}
        onConfirm={() => void handleDelete()}
      >
        Only clients with no invoices can be deleted. For a client with
        history, edit it and untick “Active client” instead.
      </ConfirmDialog>
    </div>
  );
}

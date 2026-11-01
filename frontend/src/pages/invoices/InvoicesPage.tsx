/** HR/admin invoice workspace: receivable metrics, reminder queue and ledger. */

import {
  AlertTriangle,
  Banknote,
  Clock,
  FileText,
  Plus,
  Search,
  Users,
  Wallet,
} from "lucide-react";
import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";

import {
  INVOICE_STATUS_LABELS,
  useClients,
  useInvoiceDashboard,
  useInvoices,
  useReminderQueue,
  type InvoiceDetail,
  type InvoiceListFilters,
  type InvoiceStatus,
} from "@/api/invoices";
import { Pagination } from "@/components/common/Pagination";
import { MetricCard } from "@/components/common/MetricCard";
import { EmptyState, ErrorState } from "@/components/common/states";
import { InvoiceFormDialog } from "@/components/invoices/InvoiceFormDialog";
import { InvoiceList } from "@/components/invoices/InvoiceList";
import { ReminderQueueCard } from "@/components/invoices/ReminderQueueCard";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { useDebouncedValue } from "@/lib/useDebouncedValue";
import { formatMoney } from "@/lib/format";
import { errorMessage } from "@/lib/errors";
import { PAGE_SIZE } from "@/lib/query";
import { usePage } from "@/lib/usePage";

const STATUS_OPTIONS: Array<InvoiceStatus | "overdue"> = [
  "draft",
  "sent",
  "partially_paid",
  "paid",
  "cancelled",
  "overdue",
];

function PageSkeleton() {
  return (
    <div className="mx-auto w-full max-w-7xl space-y-6" aria-busy="true">
      <div className="space-y-2">
        <Skeleton className="h-8 w-52" />
        <Skeleton className="h-4 w-80" />
      </div>
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        {Array.from({ length: 4 }).map((_, index) => (
          <Skeleton key={index} className="h-28 w-full" />
        ))}
      </div>
      <Skeleton className="h-80 w-full" />
    </div>
  );
}

function ListSkeleton() {
  return (
    <div className="space-y-2" aria-busy="true" aria-live="polite">
      {Array.from({ length: 6 }).map((_, index) => (
        <Skeleton key={index} className="h-16 w-full" />
      ))}
      <span className="sr-only">Loading invoices…</span>
    </div>
  );
}

export function InvoicesPage() {
  const navigate = useNavigate();
  const [search, setSearch] = useState("");
  const [status, setStatus] = useState("");
  const [client, setClient] = useState("");
  const [createOpen, setCreateOpen] = useState(false);
  const debouncedSearch = useDebouncedValue(search);
  const [page, setPage] = usePage(JSON.stringify([debouncedSearch, status, client]));

  const dashboard = useInvoiceDashboard();
  const queue = useReminderQueue(7);
  const clients = useClients({ page_size: 100 });
  const filters: InvoiceListFilters = {
    status: (status || undefined) as InvoiceListFilters["status"],
    client: client ? Number(client) : undefined,
    search: debouncedSearch || undefined,
    page,
    page_size: PAGE_SIZE,
  };
  const invoices = useInvoices(filters);

  const rows = invoices.data?.results ?? [];
  const allClients = clients.data?.results ?? [];
  const activeClients = allClients.filter((item) => item.is_active);
  const hasFilters = Boolean(status || client || debouncedSearch);

  function clearFilters() {
    setSearch("");
    setStatus("");
    setClient("");
    setPage(1);
  }

  function handleSaved(invoice: InvoiceDetail) {
    navigate(`/invoices/${invoice.id}`);
  }

  if (dashboard.isLoading) return <PageSkeleton />;

  if (dashboard.isError || dashboard.data === undefined) {
    return (
      <div className="mx-auto w-full max-w-7xl space-y-6">
        <h1 className="text-2xl font-semibold tracking-tight">Invoices</h1>
        <ErrorState
          title="Could not load the invoice dashboard"
          message={
            errorMessage(dashboard.error)
          }
          onRetry={() => void dashboard.refetch()}
        />
      </div>
    );
  }

  const data = dashboard.data;
  const queueRows = queue.data?.results ?? [];

  return (
    <div className="mx-auto w-full max-w-7xl space-y-6">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div className="space-y-1">
          <h1 className="text-2xl font-semibold tracking-tight">Invoices</h1>
          <p className="text-sm text-muted-foreground">
            Generate client invoices, record payments and chase what is overdue.
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Button asChild variant="outline">
            <Link to="/invoices/clients">
              <Users className="h-4 w-4" aria-hidden="true" />
              Clients
            </Link>
          </Button>
          <Button type="button" onClick={() => setCreateOpen(true)}>
            <Plus className="h-4 w-4" aria-hidden="true" />
            Generate invoice
          </Button>
        </div>
      </div>

      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <MetricCard
          label="Outstanding"
          value={formatMoney(data.outstanding_amount)}
          hint={`${data.outstanding_count} open invoice${
            data.outstanding_count === 1 ? "" : "s"
          }`}
          icon={Wallet}
        />
        <MetricCard
          label="Overdue"
          value={formatMoney(data.overdue_amount)}
          hint={`${data.overdue_count} invoice${
            data.overdue_count === 1 ? "" : "s"
          } past due`}
          icon={AlertTriangle}
        />
        <MetricCard
          label="Due in 7 days"
          value={formatMoney(data.due_soon_amount)}
          hint={`${data.due_soon_count} coming up`}
          icon={Clock}
        />
        <MetricCard
          label="Collected this month"
          value={formatMoney(data.collected_this_month)}
          hint={`${data.payments_this_month} payment${
            data.payments_this_month === 1 ? "" : "s"
          }`}
          icon={Banknote}
        />
      </div>

      {queueRows.length > 0 ? (
        <ReminderQueueCard
          queueRows={queueRows}
          onReviewOverdue={() => setStatus("overdue")}
        />
      ) : null}

      <Card>
        <CardContent className="space-y-4 p-4 sm:p-6">
          <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-4">
            <div className="relative lg:col-span-2">
              <Search
                className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground"
                aria-hidden="true"
              />
              <Input
                type="search"
                value={search}
                onChange={(event) => setSearch(event.target.value)}
                placeholder="Search invoice no., client or reference"
                aria-label="Search invoices"
                className="pl-9"
              />
            </div>
            <Select
              value={status}
              onChange={(event) => setStatus(event.target.value)}
              aria-label="Filter by invoice status"
            >
              <option value="">All statuses</option>
              {STATUS_OPTIONS.map((value) => (
                <option key={value} value={value}>
                  {value === "overdue"
                    ? "Overdue"
                    : INVOICE_STATUS_LABELS[value]}
                </option>
              ))}
            </Select>
            <Select
              value={client}
              onChange={(event) => setClient(event.target.value)}
              aria-label="Filter by client"
            >
              <option value="">All clients</option>
              {allClients.map((item) => (
                <option key={item.id} value={item.id}>
                  {item.name}
                </option>
              ))}
            </Select>
          </div>

          {invoices.isLoading ? (
            <ListSkeleton />
          ) : invoices.isError ? (
            <ErrorState
              title="Could not load invoices"
              message={
                errorMessage(invoices.error)
              }
              onRetry={() => void invoices.refetch()}
            />
          ) : rows.length === 0 ? (
            <EmptyState
              title={
                hasFilters
                  ? "No invoices match these filters"
                  : "No invoices yet"
              }
              description={
                hasFilters
                  ? "Try a different status, client or search."
                  : "Add a client, then generate your first invoice."
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
                ) : (
                  <Button type="button" size="sm" onClick={() => setCreateOpen(true)}>
                    Generate invoice
                  </Button>
                )
              }
            />
          ) : (
            <>
              <InvoiceList rows={rows} />

              <Pagination
                page={invoices.data?.page ?? page}
                pages={invoices.data?.pages ?? 1}
                count={invoices.data?.count ?? rows.length}
                pageSize={invoices.data?.page_size ?? PAGE_SIZE}
                onPageChange={setPage}
              />
            </>
          )}
        </CardContent>
      </Card>

      <p className="flex items-center gap-2 text-xs text-muted-foreground">
        <FileText className="h-3.5 w-3.5" aria-hidden="true" />
        Invoices are permanent financial records. Drafts can be edited; sent
        invoices can be cancelled only before a payment is recorded.
      </p>

      <InvoiceFormDialog
        open={createOpen}
        onOpenChange={setCreateOpen}
        clients={activeClients}
        onSaved={handleSaved}
      />
    </div>
  );
}

/** Renders an audit entry's JSON changes as a readable table. */

import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";

type ChangeRow = {
  field: string;
  before?: unknown;
  after?: unknown;
};

type ChangesMode = "diff" | "after" | "before" | "raw";

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function fieldLabel(field: string): string {
  return field
    .replace(/_/g, " ")
    .replace(/\b\w/g, (character) => character.toUpperCase());
}

function formatValue(value: unknown): string {
  if (value === null || value === undefined) return "—";
  if (typeof value === "boolean") return value ? "Yes" : "No";
  if (typeof value === "object") return JSON.stringify(value);
  return String(value);
}

function readChanges(changes: Record<string, unknown>): {
  mode: ChangesMode;
  rows: ChangeRow[];
} {
  if (isRecord(changes.changes)) {
    return {
      mode: "diff",
      rows: Object.entries(changes.changes).map(([field, value]) => {
        const pair = isRecord(value) ? value : { after: value };
        return { field, before: pair.before, after: pair.after };
      }),
    };
  }
  if (isRecord(changes.after)) {
    return {
      mode: "after",
      rows: Object.entries(changes.after).map(([field, value]) => ({
        field,
        after: value,
      })),
    };
  }
  if (isRecord(changes.before)) {
    return {
      mode: "before",
      rows: Object.entries(changes.before).map(([field, value]) => ({
        field,
        before: value,
      })),
    };
  }
  return { mode: "raw", rows: [] };
}

export function AuditChanges({
  changes,
}: {
  changes: Record<string, unknown>;
}) {
  const { mode, rows } = readChanges(changes);

  if (mode === "raw") {
    return (
      <pre className="max-h-72 overflow-auto rounded-md bg-muted p-3 text-xs">
        {JSON.stringify(changes, null, 2)}
      </pre>
    );
  }

  if (rows.length === 0) {
    return (
      <p className="text-sm text-muted-foreground">
        No field changes were recorded.
      </p>
    );
  }

  const hasBefore = mode !== "after";
  const hasAfter = mode !== "before";

  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>Field</TableHead>
          {hasBefore ? <TableHead>Before</TableHead> : null}
          {hasAfter ? <TableHead>After</TableHead> : null}
        </TableRow>
      </TableHeader>
      <TableBody>
        {rows.map((row) => (
          <TableRow key={row.field}>
            <TableCell className="align-top font-medium">
              {fieldLabel(row.field)}
            </TableCell>
            {hasBefore ? (
              <TableCell className="max-w-[220px] break-words align-top font-mono text-xs">
                {formatValue(row.before)}
              </TableCell>
            ) : null}
            {hasAfter ? (
              <TableCell className="max-w-[220px] break-words align-top font-mono text-xs">
                {formatValue(row.after)}
              </TableCell>
            ) : null}
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}

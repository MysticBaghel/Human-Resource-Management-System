/** Teams: HR and admin create and edit them; each can have an employee lead. */

import { zodResolver } from "@hookform/resolvers/zod";
import { Plus, Search } from "lucide-react";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";

import { ApiError } from "@/api/client";
import { useEmployees } from "@/api/employees";
import {
  type Team,
  useCreateTeam,
  useTeams,
  useUpdateTeam,
} from "@/api/teams";
import { EmptyState, ErrorState } from "@/components/common/states";
import { Field } from "@/components/form/Field";
import { FormError } from "@/components/form/FieldError";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Dialog } from "@/components/ui/dialog";
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
import { toast } from "@/components/ui/toast";
import { useDebouncedValue } from "@/lib/useDebouncedValue";

const teamSchema = z.object({
  name: z.string().trim().min(1, "A team name is required."),
  lead: z.string(),
});

type TeamFormValues = z.infer<typeof teamSchema>;

type DialogState = { mode: "create" } | { mode: "edit"; team: Team };

function TeamDialog({
  state,
  onClose,
}: {
  state: DialogState;
  onClose: () => void;
}) {
  const team = state.mode === "edit" ? state.team : undefined;
  const isEdit = team !== undefined;

  const [formError, setFormError] = useState<string | null>(null);
  const { data: colleagues } = useEmployees({ page_size: 100 });
  const createMutation = useCreateTeam();
  const updateMutation = useUpdateTeam(team?.id ?? 0);
  const isSaving = createMutation.isPending || updateMutation.isPending;

  const {
    register,
    handleSubmit,
    setError,
    formState: { errors },
  } = useForm<TeamFormValues>({
    resolver: zodResolver(teamSchema),
    defaultValues: {
      name: team?.name ?? "",
      lead: team?.lead ? String(team.lead) : "",
    },
  });

  async function onSubmit(values: TeamFormValues) {
    setFormError(null);
    const payload = {
      name: values.name.trim(),
      lead: values.lead ? Number(values.lead) : null,
    };

    try {
      if (isEdit) {
        await updateMutation.mutateAsync(payload);
        toast({ title: "Team updated", variant: "success" });
      } else {
        await createMutation.mutateAsync(payload);
        toast({ title: "Team created", variant: "success" });
      }
      onClose();
    } catch (caught) {
      if (caught instanceof ApiError) {
        if (caught.fields.name) {
          setError("name", { message: caught.fields.name[0] });
          return;
        }
        setFormError(caught.message);
        return;
      }
      setFormError("Could not reach the server. Please try again.");
    }
  }

  return (
    <Dialog
      open
      onOpenChange={(open) => {
        if (!open) onClose();
      }}
      title={team ? `Edit ${team.name}` : "New team"}
      description={
        isEdit
          ? "Change the name or choose a different lead."
          : "Teams group people and decide which manager approves their leave."
      }
      footer={
        <>
          <Button type="button" variant="outline" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" form="team-form" disabled={isSaving}>
            {isSaving ? "Saving…" : isEdit ? "Save changes" : "Create team"}
          </Button>
        </>
      }
    >
      <form id="team-form" onSubmit={handleSubmit(onSubmit)} className="space-y-4" noValidate>
        <FormError message={formError ?? undefined} />

        <Field id="name" label="Team name" error={errors.name?.message}>
          <Input
            id="name"
            aria-invalid={errors.name ? true : undefined}
            aria-describedby={errors.name ? "name-error" : undefined}
            {...register("name")}
          />
        </Field>

        <Field
          id="lead"
          label="Team lead"
          error={errors.lead?.message}
          hint="The lead approves leave for this team. Optional."
        >
          <Select id="lead" {...register("lead")}>
            <option value="">No lead</option>
            {colleagues?.results.map((colleague) => (
              <option key={colleague.id} value={colleague.id}>
                {colleague.full_name}
              </option>
            ))}
          </Select>
        </Field>
      </form>
    </Dialog>
  );
}

function ListSkeleton() {
  return (
    <div className="space-y-2" aria-busy="true" aria-live="polite">
      {Array.from({ length: 4 }).map((_, index) => (
        <Skeleton key={index} className="h-14 w-full" />
      ))}
      <span className="sr-only">Loading teams…</span>
    </div>
  );
}

export function TeamsPage() {
  const [search, setSearch] = useState("");
  const [dialog, setDialog] = useState<DialogState | null>(null);
  const debouncedSearch = useDebouncedValue(search);
  const { data, isLoading, isError, error, refetch } = useTeams(debouncedSearch);
  const rows = data?.results ?? [];

  return (
    <div className="mx-auto w-full max-w-5xl space-y-6">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div className="space-y-1">
          <h1 className="text-2xl font-semibold tracking-tight">Teams</h1>
          <p className="text-sm text-muted-foreground">
            {data ? `${data.count} ${data.count === 1 ? "team" : "teams"}` : "Group people and their leads"}
          </p>
        </div>
        <Button type="button" onClick={() => setDialog({ mode: "create" })}>
          <Plus className="h-4 w-4" aria-hidden="true" />
          New team
        </Button>
      </div>

      <Card>
        <CardContent className="space-y-4 p-4 sm:p-6">
          <div className="relative sm:max-w-sm">
            <Search
              className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground"
              aria-hidden="true"
            />
            <Input
              type="search"
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              placeholder="Search teams or leads"
              aria-label="Search teams"
              className="pl-9"
            />
          </div>

          {isLoading ? (
            <ListSkeleton />
          ) : isError ? (
            <ErrorState
              title="Could not load teams"
              message={error instanceof Error ? error.message : undefined}
              onRetry={() => void refetch()}
            />
          ) : rows.length === 0 ? (
            <EmptyState
              title={debouncedSearch ? "No teams match this search" : "No teams yet"}
              description={
                debouncedSearch
                  ? "Try a different name."
                  : "Create a team, then assign people to it when you add or edit them."
              }
              action={
                debouncedSearch ? undefined : (
                  <Button
                    type="button"
                    size="sm"
                    onClick={() => setDialog({ mode: "create" })}
                  >
                    Create the first team
                  </Button>
                )
              }
            />
          ) : (
            <>
              <div className="hidden sm:block">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Team</TableHead>
                      <TableHead>Lead</TableHead>
                      <TableHead>Members</TableHead>
                      <TableHead className="text-right">Actions</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {rows.map((team) => (
                      <TableRow key={team.id}>
                        <TableCell className="font-medium">{team.name}</TableCell>
                        <TableCell>{team.lead_name ?? "No lead"}</TableCell>
                        <TableCell>{team.member_count}</TableCell>
                        <TableCell className="text-right">
                          <Button
                            type="button"
                            variant="ghost"
                            size="sm"
                            onClick={() => setDialog({ mode: "edit", team })}
                          >
                            Edit
                          </Button>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>

              <ul className="space-y-2 sm:hidden">
                {rows.map((team) => (
                  <li key={team.id} className="rounded-lg border p-3">
                    <div className="flex items-start justify-between gap-2">
                      <div className="min-w-0">
                        <p className="truncate text-sm font-medium">{team.name}</p>
                        <p className="truncate text-xs text-muted-foreground">
                          {team.lead_name ?? "No lead"} · {team.member_count}{" "}
                          {team.member_count === 1 ? "member" : "members"}
                        </p>
                      </div>
                      <Button
                        type="button"
                        variant="outline"
                        size="sm"
                        onClick={() => setDialog({ mode: "edit", team })}
                      >
                        Edit
                      </Button>
                    </div>
                  </li>
                ))}
              </ul>
            </>
          )}
        </CardContent>
      </Card>

      {dialog ? (
        <TeamDialog
          key={dialog.mode === "edit" ? dialog.team.id : "new"}
          state={dialog}
          onClose={() => setDialog(null)}
        />
      ) : null}
    </div>
  );
}

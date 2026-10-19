/** Create or edit an employee. New employees get an invite, not a password. */

import { zodResolver } from "@hookform/resolvers/zod";
import { ArrowLeft } from "lucide-react";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { Link, useNavigate, useParams } from "react-router-dom";
import { z } from "zod";

import { ApiError } from "@/api/client";
import {
  type Employee,
  type EmployeeInput,
  EMPLOYMENT_TYPE_LABELS,
  useCreateEmployee,
  useEmployee,
  useEmployees,
  useUpdateEmployee,
} from "@/api/employees";
import { ROLE_LABELS, type Role } from "@/api/queries";
import { useTeams } from "@/api/teams";
import { useAuth } from "@/auth/AuthContext";
import { ErrorState } from "@/components/common/states";
import { Field } from "@/components/form/Field";
import { FormError } from "@/components/form/FieldError";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { toast } from "@/components/ui/toast";

const employeeSchema = z.object({
  email: z
    .string()
    .min(1, "Email is required.")
    .email("Enter a valid email address."),
  first_name: z.string().trim().min(1, "First name is required."),
  last_name: z.string().trim().min(1, "Last name is required."),
  phone: z.string().max(30, "Phone is too long."),
  job_title: z.string().max(120, "Job title is too long."),
  team: z.string(),
  manager: z.string(),
  start_date: z.string().min(1, "Start date is required."),
  employment_type: z.enum(["full_time", "part_time", "contract", "intern"]),
  role: z.enum(["employee", "manager", "hr", "admin"]),
});

type FormValues = z.infer<typeof employeeSchema>;

const EMPTY_FORM: FormValues = {
  email: "",
  first_name: "",
  last_name: "",
  phone: "",
  job_title: "",
  team: "",
  manager: "",
  start_date: "",
  employment_type: "full_time",
  role: "employee",
};

function toFormValues(employee: Employee): FormValues {
  return {
    email: employee.email,
    first_name: employee.first_name,
    last_name: employee.last_name,
    phone: employee.phone,
    job_title: employee.job_title,
    team: employee.team ? String(employee.team) : "",
    manager: employee.manager ? String(employee.manager) : "",
    start_date: employee.start_date,
    employment_type: employee.employment_type,
    role: employee.role,
  };
}

function BackLink({ to, label }: { to: string; label: string }) {
  return (
    <Link
      to={to}
      className="inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground"
    >
      <ArrowLeft className="h-4 w-4" aria-hidden="true" />
      {label}
    </Link>
  );
}

function PageSkeleton() {
  return (
    <div className="mx-auto w-full max-w-3xl space-y-6" aria-busy="true" aria-live="polite">
      <Skeleton className="h-4 w-24" />
      <Skeleton className="h-8 w-56" />
      <Skeleton className="h-64 w-full" />
      <span className="sr-only">Loading employee…</span>
    </div>
  );
}

function EmployeeForm({ employee }: { employee?: Employee }) {
  const navigate = useNavigate();
  const { user } = useAuth();
  const isEdit = employee !== undefined;
  const isAdmin = user?.role === "admin";

  const [formError, setFormError] = useState<string | null>(null);
  const { data: teams, isLoading: teamsLoading } = useTeams();
  const { data: colleagues } = useEmployees({ page_size: 100 });

  const createMutation = useCreateEmployee();
  const updateMutation = useUpdateEmployee(employee?.id ?? 0);
  const isSaving = createMutation.isPending || updateMutation.isPending;

  const {
    register,
    handleSubmit,
    setError,
    formState: { errors },
  } = useForm<FormValues>({
    resolver: zodResolver(employeeSchema),
    defaultValues: employee ? toFormValues(employee) : EMPTY_FORM,
  });

  // Only an admin may hand out the admin role; everyone else can still make
  // managers and HR users.
  const roleOptions: Role[] = isAdmin
    ? ["employee", "manager", "hr", "admin"]
    : ["employee", "manager", "hr"];
  const roleLocked = !isAdmin && employee?.role === "admin";

  const managerOptions = (colleagues?.results ?? []).filter(
    (colleague) => colleague.id !== employee?.id,
  );

  async function onSubmit(values: FormValues) {
    setFormError(null);

    const payload: EmployeeInput = {
      email: values.email.trim(),
      first_name: values.first_name.trim(),
      last_name: values.last_name.trim(),
      phone: values.phone.trim(),
      job_title: values.job_title.trim(),
      team: values.team ? Number(values.team) : null,
      manager: values.manager ? Number(values.manager) : null,
      start_date: values.start_date,
      employment_type: values.employment_type,
      role: values.role,
    };

    try {
      const saved = isEdit
        ? await updateMutation.mutateAsync(payload)
        : await createMutation.mutateAsync(payload);

      toast({
        title: isEdit ? "Employee updated" : "Employee created",
        description: isEdit
          ? `${saved.full_name} has been saved.`
          : `An invite link has been emailed to ${saved.email}.`,
        variant: "success",
      });
      navigate(`/employees/${saved.id}`, { replace: true });
    } catch (caught) {
      if (caught instanceof ApiError) {
        let fieldHandled = false;
        for (const [field, messages] of Object.entries(caught.fields)) {
          if (Object.keys(employeeSchema.shape).includes(field)) {
            setError(field as keyof FormValues, { message: messages[0] });
            fieldHandled = true;
          }
        }
        if (!fieldHandled) setFormError(caught.message);
        return;
      }
      setFormError("Could not reach the server. Please try again.");
    }
  }

  return (
    <div className="mx-auto w-full max-w-3xl space-y-6">
      <BackLink
        to={isEdit && employee ? `/employees/${employee.id}` : "/employees"}
        label={isEdit ? "Back to profile" : "Employees"}
      />

      <div className="space-y-1">
        <h1 className="text-2xl font-semibold tracking-tight">
          {isEdit && employee ? `Edit ${employee.full_name}` : "New employee"}
        </h1>
        <p className="text-sm text-muted-foreground">
          {isEdit
            ? "Changes are recorded in the audit log."
            : "We create the login and email a one-time link so they choose their own password."}
        </p>
      </div>

      <form onSubmit={handleSubmit(onSubmit)} className="space-y-6" noValidate>
        <FormError message={formError ?? undefined} />

        <Card>
          <CardHeader>
            <CardTitle className="text-base">Person</CardTitle>
          </CardHeader>
          <CardContent className="grid gap-4 sm:grid-cols-2">
            <Field id="first_name" label="First name" error={errors.first_name?.message}>
              <Input
                id="first_name"
                autoComplete="given-name"
                aria-invalid={errors.first_name ? true : undefined}
                aria-describedby={errors.first_name ? "first_name-error" : undefined}
                {...register("first_name")}
              />
            </Field>

            <Field id="last_name" label="Last name" error={errors.last_name?.message}>
              <Input
                id="last_name"
                autoComplete="family-name"
                aria-invalid={errors.last_name ? true : undefined}
                aria-describedby={errors.last_name ? "last_name-error" : undefined}
                {...register("last_name")}
              />
            </Field>

            <Field
              id="email"
              label="Work email"
              error={errors.email?.message}
              hint={isEdit ? "Changing this changes their sign-in address." : "The invite goes here."}
            >
              <Input
                id="email"
                type="email"
                autoComplete="email"
                aria-invalid={errors.email ? true : undefined}
                aria-describedby={errors.email ? "email-error" : undefined}
                {...register("email")}
              />
            </Field>

            <Field id="phone" label="Phone" error={errors.phone?.message} hint="Optional.">
              <Input
                id="phone"
                type="tel"
                autoComplete="tel"
                aria-invalid={errors.phone ? true : undefined}
                aria-describedby={errors.phone ? "phone-error" : undefined}
                {...register("phone")}
              />
            </Field>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-base">Employment</CardTitle>
          </CardHeader>
          <CardContent className="grid gap-4 sm:grid-cols-2">
            <Field id="job_title" label="Job title" error={errors.job_title?.message}>
              <Input
                id="job_title"
                aria-invalid={errors.job_title ? true : undefined}
                aria-describedby={errors.job_title ? "job_title-error" : undefined}
                {...register("job_title")}
              />
            </Field>

            <Field id="start_date" label="Start date" error={errors.start_date?.message}>
              <Input
                id="start_date"
                type="date"
                aria-invalid={errors.start_date ? true : undefined}
                aria-describedby={errors.start_date ? "start_date-error" : undefined}
                {...register("start_date")}
              />
            </Field>

            <Field id="team" label="Team" error={errors.team?.message}>
              <Select id="team" {...register("team")}>
                <option value="">{teamsLoading ? "Loading teams…" : "No team"}</option>
                {teams?.results.map((team) => (
                  <option key={team.id} value={team.id}>
                    {team.name}
                  </option>
                ))}
              </Select>
            </Field>

            <Field
              id="manager"
              label="Manager"
              error={errors.manager?.message}
              hint="Approves their leave. HR approves when there is none."
            >
              <Select id="manager" {...register("manager")}>
                <option value="">No manager</option>
                {managerOptions.map((colleague) => (
                  <option key={colleague.id} value={colleague.id}>
                    {colleague.full_name}
                  </option>
                ))}
              </Select>
            </Field>

            <Field
              id="employment_type"
              label="Employment type"
              error={errors.employment_type?.message}
            >
              <Select id="employment_type" {...register("employment_type")}>
                {Object.entries(EMPLOYMENT_TYPE_LABELS).map(([value, label]) => (
                  <option key={value} value={value}>
                    {label}
                  </option>
                ))}
              </Select>
            </Field>

            <Field
              id="role"
              label="Access role"
              error={errors.role?.message}
              hint={
                roleLocked
                  ? "Only an admin can change an admin's role."
                  : "Admin can only be granted by an admin."
              }
            >
              {roleLocked && employee ? (
                <Input id="role" value={ROLE_LABELS[employee.role]} disabled readOnly />
              ) : (
                <Select id="role" {...register("role")}>
                  {roleOptions.map((option) => (
                    <option key={option} value={option}>
                      {ROLE_LABELS[option]}
                    </option>
                  ))}
                </Select>
              )}
            </Field>
          </CardContent>
        </Card>

        <div className="flex flex-col-reverse gap-2 sm:flex-row sm:justify-end">
          <Button asChild variant="outline">
            <Link to={isEdit && employee ? `/employees/${employee.id}` : "/employees"}>
              Cancel
            </Link>
          </Button>
          <Button type="submit" disabled={isSaving}>
            {isSaving
              ? "Saving…"
              : isEdit
                ? "Save changes"
                : "Create and send invite"}
          </Button>
        </div>
      </form>
    </div>
  );
}

export function EmployeeFormPage() {
  const params = useParams();
  const employeeId = params.id ? Number(params.id) : undefined;
  const isEdit = employeeId !== undefined;
  const { data: employee, isLoading, isError, error, refetch } = useEmployee(
    isEdit ? employeeId : undefined,
  );

  if (isEdit && isLoading) return <PageSkeleton />;

  if (isEdit && (isError || employee === undefined)) {
    const notFound = error instanceof ApiError && error.status === 404;
    return (
      <div className="mx-auto w-full max-w-3xl space-y-6">
        <BackLink to="/employees" label="Employees" />
        <ErrorState
          title={notFound ? "Employee not found" : "Could not load this employee"}
          message={error instanceof Error ? error.message : undefined}
          onRetry={notFound ? undefined : () => void refetch()}
        />
      </div>
    );
  }

  return <EmployeeForm key={employee?.id ?? "new"} employee={employee} />;
}

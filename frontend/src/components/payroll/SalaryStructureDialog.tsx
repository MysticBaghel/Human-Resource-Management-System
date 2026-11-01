/** Create or revise a salary structure. The API records the revision. */

import { zodResolver } from "@hookform/resolvers/zod";
import { useEffect, useState } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";

import { ApiError } from "@/api/client";
import type { Employee } from "@/api/employees";
import {
  DEDUCTION_FIELDS,
  DEDUCTION_LABELS,
  EARNING_FIELDS,
  EARNING_LABELS,
  useCreateSalaryStructure,
  useRevokeSalaryStructure,
  useUpdateSalaryStructure,
  type SalaryStructure,
} from "@/api/payroll";
import { ConfirmDialog } from "@/components/common/ConfirmDialog";
import { Field } from "@/components/form/Field";
import { FormError } from "@/components/form/FieldError";
import { SalaryBreakdown } from "@/components/payroll/SalaryBreakdown";
import { Button } from "@/components/ui/button";
import { Dialog } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { toast } from "@/components/ui/toast";
import { toIsoDate } from "@/lib/date";

const money = z
  .number({ invalid_type_error: "Enter a valid amount." })
  .min(0, "An amount cannot be negative.");

const schema = z.object({
  employee: z.string().min(1, "Choose an employee."),
  effective_date: z.string().min(1, "Choose an effective date."),
  basic_salary: money,
  hra: money,
  conveyance_allowance: money,
  medical_allowance: money,
  special_allowance: money,
  other_allowances: money,
  provident_fund: money,
  professional_tax: money,
  income_tax: money,
  other_deductions: money,
  reason: z.string().max(255, "Keep the reason under 255 characters."),
});

type FormValues = z.infer<typeof schema>;

function blankValues(): FormValues {
  return {
    employee: "",
    effective_date: toIsoDate(new Date()),
    basic_salary: 0,
    hra: 0,
    conveyance_allowance: 0,
    medical_allowance: 0,
    special_allowance: 0,
    other_allowances: 0,
    provident_fund: 0,
    professional_tax: 0,
    income_tax: 0,
    other_deductions: 0,
    reason: "",
  };
}

function toFormValues(structure: SalaryStructure): FormValues {
  return {
    employee: String(structure.employee),
    effective_date: structure.effective_date,
    basic_salary: structure.basic_salary,
    hra: structure.hra,
    conveyance_allowance: structure.conveyance_allowance,
    medical_allowance: structure.medical_allowance,
    special_allowance: structure.special_allowance,
    other_allowances: structure.other_allowances,
    provident_fund: structure.provident_fund,
    professional_tax: structure.professional_tax,
    income_tax: structure.income_tax,
    other_deductions: structure.other_deductions,
    reason: "",
  };
}

function moneyString(value: number): string {
  return value.toFixed(2);
}

type SalaryStructureDialogProps = {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  employees: Employee[];
  structure?: SalaryStructure | null;
};

export function SalaryStructureDialog({
  open,
  onOpenChange,
  employees,
  structure,
}: SalaryStructureDialogProps) {
  const isEdit = structure !== undefined && structure !== null;
  const createMutation = useCreateSalaryStructure();
  const updateMutation = useUpdateSalaryStructure(structure?.id ?? 0);
  const revokeMutation = useRevokeSalaryStructure();
  const isSaving = createMutation.isPending || updateMutation.isPending;
  const [formError, setFormError] = useState<string | null>(null);
  const [revokeOpen, setRevokeOpen] = useState(false);

  const {
    register,
    handleSubmit,
    reset,
    watch,
    setError,
    formState: { errors },
  } = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: blankValues(),
  });

  useEffect(() => {
    if (!open) return;
    setFormError(null);
    setRevokeOpen(false);
    reset(structure ? toFormValues(structure) : blankValues());
  }, [open, structure, reset]);

  const values = watch();
  const preview = {
    basic_salary: Number(values.basic_salary) || 0,
    hra: Number(values.hra) || 0,
    conveyance_allowance: Number(values.conveyance_allowance) || 0,
    medical_allowance: Number(values.medical_allowance) || 0,
    special_allowance: Number(values.special_allowance) || 0,
    other_allowances: Number(values.other_allowances) || 0,
    provident_fund: Number(values.provident_fund) || 0,
    professional_tax: Number(values.professional_tax) || 0,
    income_tax: Number(values.income_tax) || 0,
    other_deductions: Number(values.other_deductions) || 0,
    gross_salary: 0,
    total_deductions: 0,
    net_salary: 0,
  };
  preview.gross_salary = EARNING_FIELDS.reduce(
    (total, field) => total + preview[field],
    0,
  );
  preview.total_deductions = DEDUCTION_FIELDS.reduce(
    (total, field) => total + preview[field],
    0,
  );
  preview.net_salary = preview.gross_salary - preview.total_deductions;

  async function onSubmit(form: FormValues) {
    setFormError(null);
    const payload = {
      employee: Number(form.employee),
      basic_salary: moneyString(form.basic_salary),
      hra: moneyString(form.hra),
      conveyance_allowance: moneyString(form.conveyance_allowance),
      medical_allowance: moneyString(form.medical_allowance),
      special_allowance: moneyString(form.special_allowance),
      other_allowances: moneyString(form.other_allowances),
      provident_fund: moneyString(form.provident_fund),
      professional_tax: moneyString(form.professional_tax),
      income_tax: moneyString(form.income_tax),
      other_deductions: moneyString(form.other_deductions),
      effective_date: form.effective_date,
      reason: form.reason.trim(),
    };

    try {
      if (isEdit) {
        await updateMutation.mutateAsync(payload);
      } else {
        await createMutation.mutateAsync(payload);
      }
      toast({
        title: isEdit ? "Salary revised" : "Salary structure created",
        description: isEdit
          ? `The revision is effective ${form.effective_date}.`
          : `Net salary is calculated at generation time.`,
        variant: "success",
      });
      onOpenChange(false);
    } catch (caught) {
      if (caught instanceof ApiError) {
        let handled = false;
        for (const [field, messages] of Object.entries(caught.fields)) {
          if (field in schema.shape) {
            setError(field as keyof FormValues, { message: messages[0] });
            handled = true;
          }
        }
        if (!handled) setFormError(caught.message);
        return;
      }
      setFormError("Could not reach the server. Please try again.");
    }
  }

  async function handleRevoke() {
    if (!structure) return;
    setFormError(null);
    try {
      await revokeMutation.mutateAsync(structure.id);
      toast({
        title: "Salary structure revoked",
        description: `${structure.employee_name} will be skipped by future payroll runs until a new structure is created.`,
        variant: "success",
      });
      setRevokeOpen(false);
      onOpenChange(false);
    } catch (caught) {
      setRevokeOpen(false);
      setFormError(
        caught instanceof ApiError
          ? caught.message
          : "Could not revoke the salary structure.",
      );
    }
  }

  return (
    <Dialog
      open={open}
      onOpenChange={onOpenChange}
      title={isEdit ? "Revise salary structure" : "New salary structure"}
      description={
        isEdit
          ? "Saving creates a new active version and keeps this one in revision history."
          : "Earnings and deductions are snapshotted into each payroll run."
      }
      className="sm:max-w-3xl"
      footer={
        <>
          {isEdit ? (
            <Button
              type="button"
              variant="destructive"
              onClick={() => setRevokeOpen(true)}
              disabled={isSaving || revokeMutation.isPending}
            >
              Revoke
            </Button>
          ) : null}
          <Button
            type="button"
            variant="outline"
            onClick={() => onOpenChange(false)}
            disabled={isSaving}
          >
            Cancel
          </Button>
          <Button
            type="submit"
            form="salary-structure-form"
            disabled={isSaving}
          >
            {isSaving
              ? "Saving…"
              : isEdit
                ? "Save revision"
                : "Create structure"}
          </Button>
        </>
      }
    >
      <form
        id="salary-structure-form"
        onSubmit={handleSubmit(onSubmit)}
        className="space-y-5"
        noValidate
      >
        <FormError message={formError ?? undefined} />

        <div className="grid gap-4 sm:grid-cols-2">
          {isEdit && structure ? (
            <>
              <input type="hidden" {...register("employee")} />
              <Field id="employee-display" label="Employee">
                <Input
                  id="employee-display"
                  value={`${structure.employee_name} (${structure.employee_code})`}
                  disabled
                  readOnly
                />
              </Field>
            </>
          ) : (
            <Field
              id="employee"
              label="Employee"
              error={errors.employee?.message}
              hint="Only people without an active structure are listed."
            >
              <Select
                id="employee"
                aria-invalid={errors.employee ? true : undefined}
                {...register("employee")}
              >
                <option value="">Choose an employee</option>
                {employees.map((employee) => (
                  <option key={employee.id} value={employee.id}>
                    {employee.full_name}
                    {employee.job_title ? ` · ${employee.job_title}` : ""}
                  </option>
                ))}
              </Select>
            </Field>
          )}

          <Field
            id="effective_date"
            label="Effective date"
            error={errors.effective_date?.message}
            hint="A revision cannot predate the current structure."
          >
            <Input
              id="effective_date"
              type="date"
              min={isEdit && structure ? structure.effective_date : undefined}
              aria-invalid={errors.effective_date ? true : undefined}
              {...register("effective_date")}
            />
          </Field>
        </div>

        <div className="grid gap-4 sm:grid-cols-2">
          <div className="space-y-3 rounded-lg border bg-muted/20 p-3">
            <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
              Earnings
            </p>
            {EARNING_FIELDS.map((field) => (
              <Field
                key={field}
                id={field}
                label={EARNING_LABELS[field]}
                error={errors[field]?.message}
              >
                <Input
                  id={field}
                  type="number"
                  inputMode="decimal"
                  min="0"
                  step="0.01"
                  {...register(field, { valueAsNumber: true })}
                />
              </Field>
            ))}
          </div>

          <div className="space-y-3 rounded-lg border bg-muted/20 p-3">
            <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
              Deductions
            </p>
            {DEDUCTION_FIELDS.map((field) => (
              <Field
                key={field}
                id={field}
                label={DEDUCTION_LABELS[field]}
                error={errors[field]?.message}
              >
                <Input
                  id={field}
                  type="number"
                  inputMode="decimal"
                  min="0"
                  step="0.01"
                  {...register(field, { valueAsNumber: true })}
                />
              </Field>
            ))}
          </div>
        </div>

        {isEdit ? (
          <Field
            id="reason"
            label="Revision reason"
            error={errors.reason?.message}
            hint="Optional. Shown in revision history."
          >
            <Textarea
              id="reason"
              rows={2}
              placeholder="Annual revision, promotion, market correction…"
              {...register("reason")}
            />
          </Field>
        ) : null}

        <div className="space-y-2">
          <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
            Live preview
          </p>
          <SalaryBreakdown values={preview} />
        </div>
      </form>

      {isEdit && structure ? (
        <ConfirmDialog
          open={revokeOpen}
          onOpenChange={(nextOpen) => {
            if (!nextOpen) setRevokeOpen(false);
          }}
          title="Revoke this salary structure?"
          description={`${structure.employee_name} · effective ${structure.effective_date}`}
          cancelLabel="Keep structure"
          confirmLabel="Revoke"
          pendingLabel="Revoking…"
          isPending={revokeMutation.isPending}
          onConfirm={() => void handleRevoke()}
        >
          The structure stays in revision history and existing payroll snapshots
          are untouched. Future payroll runs will skip this employee until a new
          structure is created.
        </ConfirmDialog>
      ) : null}
    </Dialog>
  );
}

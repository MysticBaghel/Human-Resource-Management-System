/** Generate draft payroll for one employee or every eligible employee. */

import { zodResolver } from "@hookform/resolvers/zod";
import { useEffect, useState } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";

import { ApiError } from "@/api/client";
import type { Employee } from "@/api/employees";
import { MONTH_NAMES, useGeneratePayroll } from "@/api/payroll";
import { Field } from "@/components/form/Field";
import { FormError } from "@/components/form/FieldError";
import { Button } from "@/components/ui/button";
import { Dialog } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import { toast } from "@/components/ui/toast";

const schema = z.object({
  month: z.number().min(1).max(12),
  year: z.number().min(2000).max(2100),
  employee: z.string(),
});

type FormValues = z.infer<typeof schema>;

type GeneratePayrollDialogProps = {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  month: number;
  year: number;
  employees: Employee[];
  onGenerated?: (month: number, year: number) => void;
};

export function GeneratePayrollDialog({
  open,
  onOpenChange,
  month,
  year,
  employees,
  onGenerated,
}: GeneratePayrollDialogProps) {
  const mutation = useGeneratePayroll();
  const [formError, setFormError] = useState<string | null>(null);
  const {
    register,
    handleSubmit,
    reset,
    setError,
    formState: { errors },
  } = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: { month, year, employee: "" },
  });

  useEffect(() => {
    if (!open) return;
    setFormError(null);
    reset({ month, year, employee: "" });
  }, [open, month, year, reset]);

  async function onSubmit(values: FormValues) {
    setFormError(null);
    try {
      const result = await mutation.mutateAsync({
        month: values.month,
        year: values.year,
        employee: values.employee ? Number(values.employee) : undefined,
      });
      const description =
        result.skipped_count > 0
          ? `${result.generated_count} generated, ${result.skipped_count} skipped (already paid or no structure).`
          : `${result.generated_count} draft payroll record${
              result.generated_count === 1 ? "" : "s"
            } created.`;
      toast({
        title: result.generated_count > 0 ? "Payroll generated" : "Nothing generated",
        description,
        variant: result.generated_count > 0 ? "success" : "default",
      });
      onGenerated?.(values.month, values.year);
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

  return (
    <Dialog
      open={open}
      onOpenChange={onOpenChange}
      title="Generate payroll"
      description="Salary values are copied from the structure that applies to the period. Future changes never rewrite these records."
      footer={
        <>
          <Button
            type="button"
            variant="outline"
            onClick={() => onOpenChange(false)}
            disabled={mutation.isPending}
          >
            Cancel
          </Button>
          <Button type="submit" form="generate-payroll-form" disabled={mutation.isPending}>
            {mutation.isPending ? "Generating…" : "Generate draft payroll"}
          </Button>
        </>
      }
    >
      <form
        id="generate-payroll-form"
        onSubmit={handleSubmit(onSubmit)}
        className="space-y-4"
        noValidate
      >
        <FormError message={formError ?? undefined} />

        <div className="grid gap-4 sm:grid-cols-2">
          <Field id="generate-month" label="Month" error={errors.month?.message}>
            <Select id="generate-month" {...register("month", { valueAsNumber: true })}>
              {MONTH_NAMES.map((name, index) => (
                <option key={name} value={index + 1}>
                  {name}
                </option>
              ))}
            </Select>
          </Field>
          <Field id="generate-year" label="Year" error={errors.year?.message}>
            <Input
              id="generate-year"
              type="number"
              min="2000"
              max="2100"
              {...register("year", { valueAsNumber: true })}
            />
          </Field>
        </div>

        <Field
          id="generate-employee"
          label="Who"
          error={errors.employee?.message}
          hint="All eligible active employees, or one person."
        >
          <Select id="generate-employee" {...register("employee")}>
            <option value="">All eligible employees</option>
            {employees
              .filter((employee) => employee.status === "active")
              .map((employee) => (
                <option key={employee.id} value={employee.id}>
                  {employee.full_name}
                </option>
              ))}
          </Select>
        </Field>

        <p className="text-xs text-muted-foreground">
          A duplicate for the same employee and period is rejected for a single
          employee, and skipped in an all-employees run.
        </p>
      </form>
    </Dialog>
  );
}

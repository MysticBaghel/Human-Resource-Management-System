/** Dialog that requests leave, with a server-computed day and balance preview. */

import { zodResolver } from "@hookform/resolvers/zod";
import { useEffect, useState } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";

import { ApiError } from "@/api/client";
import {
  type LeavePreview,
  type LeaveType,
  useCreateLeaveRequest,
  useLeavePreview,
} from "@/api/leave";
import { Field } from "@/components/form/Field";
import { FormError } from "@/components/form/FieldError";
import { Button } from "@/components/ui/button";
import { Dialog } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select } from "@/components/ui/select";
import { toast } from "@/components/ui/toast";
import { toIsoDate } from "@/lib/date";
import { cn } from "@/lib/utils";

const requestSchema = z
  .object({
    leave_type: z.string().min(1, "Choose a leave type."),
    start_date: z.string().min(1, "Pick a start date."),
    end_date: z.string().min(1, "Pick an end date."),
    half_day: z.boolean(),
  })
  .refine((values) => values.end_date >= values.start_date, {
    path: ["end_date"],
    message: "The end date cannot be before the start date.",
  });

type RequestValues = z.infer<typeof requestSchema>;

function PreviewBox({ preview }: { preview: LeavePreview }) {
  const warning =
    preview.overlap || !preview.sufficient || preview.days <= 0;

  return (
    <div
      aria-live="polite"
      className={cn(
        "space-y-1 rounded-md border px-3 py-2 text-sm",
        warning
          ? "border-amber-200 bg-amber-50 text-amber-900"
          : "bg-muted/40",
      )}
    >
      <p>
        <span className="font-semibold">{preview.days}</span> working day
        {preview.days === 1 ? "" : "s"}
        {preview.remaining !== null
          ? ` · ${preview.remaining} day${preview.remaining === 1 ? "" : "s"} remaining`
          : ""}
      </p>
      {preview.days <= 0 ? (
        <p>The selected dates contain no working days.</p>
      ) : null}
      {preview.overlap ? (
        <p>These dates overlap an existing request.</p>
      ) : null}
      {!preview.sufficient ? (
        <p>There is not enough balance for these dates.</p>
      ) : null}
    </div>
  );
}

export function RequestLeaveDialog({
  leaveTypes,
  onClose,
}: {
  leaveTypes: LeaveType[];
  onClose: () => void;
}) {
  const today = toIsoDate(new Date());
  const createMutation = useCreateLeaveRequest();
  const [formError, setFormError] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    watch,
    setValue,
    setError,
    formState: { errors },
  } = useForm<RequestValues>({
    resolver: zodResolver(requestSchema),
    defaultValues: {
      leave_type: leaveTypes[0] ? String(leaveTypes[0].id) : "",
      start_date: today,
      end_date: today,
      half_day: false,
    },
  });

  const leaveType = watch("leave_type");
  const startDate = watch("start_date");
  const endDate = watch("end_date");
  const halfDay = watch("half_day");

  // A half day only exists on a single date; clear it when the range grows.
  useEffect(() => {
    if (startDate && endDate && startDate !== endDate) {
      setValue("half_day", false);
    }
  }, [startDate, endDate, setValue]);

  const previewInput =
    leaveType && startDate && endDate && endDate >= startDate
      ? {
          leave_type: Number(leaveType),
          start_date: startDate,
          end_date: endDate,
          half_day: halfDay,
        }
      : null;

  const { data: preview, isFetching } = useLeavePreview(previewInput);

  const submitBlocked = Boolean(
    preview &&
      (preview.days <= 0 || preview.overlap || !preview.sufficient),
  );

  async function onSubmit(values: RequestValues) {
    setFormError(null);
    try {
      const created = await createMutation.mutateAsync({
        leave_type: Number(values.leave_type),
        start_date: values.start_date,
        end_date: values.end_date,
        half_day: values.half_day,
      });
      toast({
        title: created.status === "approved" ? "Leave booked" : "Leave requested",
        description:
          created.status === "approved"
            ? `${created.days} day(s) deducted from your balance.`
            : "Your manager or HR will review it.",
        variant: "success",
      });
      onClose();
    } catch (caught) {
      if (caught instanceof ApiError) {
        if (caught.fields.end_date) {
          setError("end_date", { message: caught.fields.end_date[0] });
          return;
        }
        if (caught.fields.start_date) {
          setError("start_date", { message: caught.fields.start_date[0] });
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
      title="Request leave"
      description="Working days are Monday to Friday, minus company holidays."
      footer={
        <>
          <Button type="button" variant="outline" onClick={onClose}>
            Cancel
          </Button>
          <Button
            type="submit"
            form="request-leave-form"
            disabled={createMutation.isPending || submitBlocked}
          >
            {createMutation.isPending ? "Requesting…" : "Request leave"}
          </Button>
        </>
      }
    >
      <form
        id="request-leave-form"
        onSubmit={handleSubmit(onSubmit)}
        className="space-y-4"
        noValidate
      >
        <FormError message={formError ?? undefined} />

        <Field id="leave_type" label="Leave type" error={errors.leave_type?.message}>
          <Select
            id="leave_type"
            aria-invalid={errors.leave_type ? true : undefined}
            {...register("leave_type")}
          >
            {leaveTypes.map((type) => (
              <option key={type.id} value={type.id}>
                {type.name}
                {type.requires_approval ? "" : " (auto-approved)"}
              </option>
            ))}
          </Select>
        </Field>

        <div className="grid gap-4 sm:grid-cols-2">
          <Field id="start_date" label="From" error={errors.start_date?.message}>
            <Input
              id="start_date"
              type="date"
              aria-invalid={errors.start_date ? true : undefined}
              {...register("start_date")}
            />
          </Field>

          <Field id="end_date" label="To" error={errors.end_date?.message}>
            <Input
              id="end_date"
              type="date"
              aria-invalid={errors.end_date ? true : undefined}
              {...register("end_date")}
            />
          </Field>
        </div>

        <div className="flex items-center gap-2">
          <input
            id="half_day"
            type="checkbox"
            disabled={startDate !== endDate}
            className="h-4 w-4 rounded border-input"
            {...register("half_day")}
          />
          <Label htmlFor="half_day" className="font-normal">
            Half day
          </Label>
          <span className="text-xs text-muted-foreground">
            {startDate === endDate
              ? "(counts as 0.5)"
              : "(single day only)"}
          </span>
        </div>

        {previewInput ? (
          isFetching && !preview ? (
            <p className="text-sm text-muted-foreground">Checking dates…</p>
          ) : preview ? (
            <PreviewBox preview={preview} />
          ) : null
        ) : null}
      </form>
    </Dialog>
  );
}

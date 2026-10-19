/** Public page behind the invite email: choose a password and sign in. */

import { zodResolver } from "@hookform/resolvers/zod";
import { useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { z } from "zod";

import { ApiError } from "@/api/client";
import { acceptInvite, meQueryKey } from "@/api/queries";
import { Field } from "@/components/form/Field";
import { FormError } from "@/components/form/FieldError";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { toast } from "@/components/ui/toast";
import { AuthLayout } from "./AuthLayout";

const inviteSchema = z
  .object({
    password: z.string().min(8, "Use at least 8 characters."),
    confirm: z.string().min(1, "Confirm your password."),
  })
  .refine((values) => values.password === values.confirm, {
    path: ["confirm"],
    message: "Passwords do not match.",
  });

type InviteValues = z.infer<typeof inviteSchema>;

export function AcceptInvitePage() {
  const [params] = useSearchParams();
  const token = params.get("token") ?? "";
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [formError, setFormError] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    setError,
    formState: { errors, isSubmitting },
  } = useForm<InviteValues>({
    resolver: zodResolver(inviteSchema),
    defaultValues: { password: "", confirm: "" },
  });

  if (!token) {
    return (
      <AuthLayout
        title="This invite link is incomplete"
        description="The link is missing its token. Ask HR to send you a new invite."
        footer={<Link to="/login">Back to sign in</Link>}
      >
        <Button asChild className="w-full">
          <Link to="/login">Go to sign in</Link>
        </Button>
      </AuthLayout>
    );
  }

  async function onSubmit(values: InviteValues) {
    setFormError(null);
    try {
      const user = await acceptInvite(token, values.password);
      // Seed the session cache so the guards see the signed-in user at once.
      queryClient.setQueryData(meQueryKey, user);
      toast({
        title: "Welcome to HRMS",
        description: "Your password is set and you are signed in.",
        variant: "success",
      });
      navigate("/", { replace: true });
    } catch (caught) {
      if (caught instanceof ApiError) {
        if (caught.fields.password) {
          setError("password", { message: caught.fields.password[0] });
          return;
        }
        setFormError(
          caught.status === 400
            ? `${caught.message} Ask HR to send you a new invite.`
            : caught.message,
        );
        return;
      }
      setFormError("Could not reach the server. Please try again.");
    }
  }

  return (
    <AuthLayout
      title="Set your password"
      description="Choose a password for your HRMS account. You will be signed in straight away."
      footer={
        <Link to="/login" className="font-medium text-primary hover:underline">
          Back to sign in
        </Link>
      }
    >
      <form onSubmit={handleSubmit(onSubmit)} className="space-y-4" noValidate>
        <FormError message={formError ?? undefined} />

        <Field id="password" label="New password" error={errors.password?.message}>
          <Input
            id="password"
            type="password"
            autoComplete="new-password"
            placeholder="At least 8 characters"
            aria-invalid={errors.password ? true : undefined}
            aria-describedby={errors.password ? "password-error" : undefined}
            {...register("password")}
          />
        </Field>

        <Field id="confirm" label="Confirm password" error={errors.confirm?.message}>
          <Input
            id="confirm"
            type="password"
            autoComplete="new-password"
            placeholder="Type it again"
            aria-invalid={errors.confirm ? true : undefined}
            aria-describedby={errors.confirm ? "confirm-error" : undefined}
            {...register("confirm")}
          />
        </Field>

        <Button type="submit" className="w-full" disabled={isSubmitting}>
          {isSubmitting ? "Setting password…" : "Set password and sign in"}
        </Button>
      </form>
    </AuthLayout>
  );
}

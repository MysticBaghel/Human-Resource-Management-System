/** Choose a new password using the uid and token from the reset email. */

import { zodResolver } from "@hookform/resolvers/zod";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { z } from "zod";

import { ApiError } from "@/api/client";
import { confirmPasswordReset } from "@/api/queries";
import { FieldError, FormError } from "@/components/form/FieldError";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { toast } from "@/components/ui/toast";
import { AuthLayout } from "./AuthLayout";

const schema = z
  .object({
    newPassword: z.string().min(8, "Use at least 8 characters."),
    confirmPassword: z.string().min(1, "Please confirm your password."),
  })
  .refine((values) => values.newPassword === values.confirmPassword, {
    path: ["confirmPassword"],
    message: "Passwords do not match.",
  });

type Values = z.infer<typeof schema>;

export function ResetPasswordPage() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const [formError, setFormError] = useState<string | null>(null);

  const uid = searchParams.get("uid") ?? "";
  const token = searchParams.get("token") ?? "";

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<Values>({
    resolver: zodResolver(schema),
    defaultValues: { newPassword: "", confirmPassword: "" },
  });

  const linkIsIncomplete = uid === "" || token === "";

  async function onSubmit(values: Values) {
    setFormError(null);
    try {
      await confirmPasswordReset(uid, token, values.newPassword);
      toast({
        title: "Password updated",
        description: "You can sign in with your new password.",
        variant: "success",
      });
      navigate("/login", { replace: true });
    } catch (error) {
      if (error instanceof ApiError) {
        // Password-strength failures come back as field errors from Django,
        // but they are surfaced in the form-level banner the API also sends.
        setFormError(error.message);
        return;
      }
      setFormError("Could not reach the server. Please try again.");
    }
  }

  if (linkIsIncomplete) {
    return (
      <AuthLayout
        title="Link not valid"
        description="This password-reset link is missing its token."
        footer={
          <Link to="/forgot-password" className="font-medium text-primary hover:underline">
            Request a new link
          </Link>
        }
      >
        <p className="text-sm text-muted-foreground">
          Open the link from your email again, or request a fresh one.
        </p>
      </AuthLayout>
    );
  }

  return (
    <AuthLayout
      title="Choose a new password"
      description="Pick something you have not used before."
      footer={
        <Link to="/login" className="font-medium text-primary hover:underline">
          Back to sign in
        </Link>
      }
    >
      <form onSubmit={handleSubmit(onSubmit)} className="space-y-4" noValidate>
        <FormError message={formError ?? undefined} />

        <div className="space-y-1.5">
          <Label htmlFor="newPassword">New password</Label>
          <Input
            id="newPassword"
            type="password"
            autoComplete="new-password"
            aria-invalid={errors.newPassword ? true : undefined}
            aria-describedby={errors.newPassword ? "new-password-error" : undefined}
            {...register("newPassword")}
          />
          <FieldError id="new-password-error" message={errors.newPassword?.message} />
        </div>

        <div className="space-y-1.5">
          <Label htmlFor="confirmPassword">Confirm password</Label>
          <Input
            id="confirmPassword"
            type="password"
            autoComplete="new-password"
            aria-invalid={errors.confirmPassword ? true : undefined}
            aria-describedby={
              errors.confirmPassword ? "confirm-password-error" : undefined
            }
            {...register("confirmPassword")}
          />
          <FieldError
            id="confirm-password-error"
            message={errors.confirmPassword?.message}
          />
        </div>

        <Button type="submit" className="w-full" disabled={isSubmitting}>
          {isSubmitting ? "Saving…" : "Set new password"}
        </Button>
      </form>
    </AuthLayout>
  );
}

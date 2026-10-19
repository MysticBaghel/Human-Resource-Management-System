/** Shared frame for the signed-out pages: login, forgot and reset password. */

import type { ReactNode } from "react";

type AuthLayoutProps = {
  title: string;
  description?: string;
  children: ReactNode;
  footer?: ReactNode;
};

export function AuthLayout({ title, description, children, footer }: AuthLayoutProps) {
  return (
    <div className="flex min-h-screen items-center justify-center overflow-x-hidden bg-muted px-4 py-10">
      <div className="w-full max-w-sm">
        <div className="mb-6 text-center">
          <p className="text-2xl font-semibold tracking-tight">HRMS</p>
          <p className="mt-1 text-sm text-muted-foreground">
            Headcount, teams and time off
          </p>
        </div>

        <div className="rounded-lg border bg-background p-6 shadow-sm">
          <div className="mb-5 space-y-1">
            <h1 className="text-lg font-semibold tracking-tight">{title}</h1>
            {description ? (
              <p className="text-sm text-muted-foreground">{description}</p>
            ) : null}
          </div>

          {children}
        </div>

        {footer ? (
          <div className="mt-4 text-center text-sm text-muted-foreground">{footer}</div>
        ) : null}
      </div>
    </div>
  );
}

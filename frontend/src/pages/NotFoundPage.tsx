import { Link } from "react-router-dom";

import { Button } from "@/components/ui/button";

export function NotFoundPage() {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center gap-4 bg-muted px-4 text-center">
      <p className="text-5xl font-semibold tracking-tight">404</p>
      <p className="text-sm text-muted-foreground">
        That page does not exist.
      </p>
      <Button asChild>
        <Link to="/">Go to the dashboard</Link>
      </Button>
    </div>
  );
}

/** My time off: a name directory for HR/admin, the personal panel otherwise. */

import { useAuth } from "@/auth/AuthContext";
import { LeaveDirectory } from "./LeaveDirectory";
import { MyLeavePanel } from "./MyLeavePanel";

export function MyTimeOffPage() {
  const { hasRole } = useAuth();

  // HR and admin manage other people's time off from here: pick a person, then
  // see that person's balances on their own page. Everyone else sees their own.
  if (hasRole("admin", "hr")) {
    return <LeaveDirectory />;
  }

  return <MyLeavePanel />;
}

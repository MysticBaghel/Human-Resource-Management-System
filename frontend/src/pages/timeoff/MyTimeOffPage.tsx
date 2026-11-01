/** Time off: a name directory for HR/admin, the personal panel otherwise. */

import { useAuth } from "@/auth/AuthContext";
import { LeaveDirectory } from "./LeaveDirectory";
import { MyLeavePanel } from "./MyLeavePanel";

type MyTimeOffPageProps = {
  /** Force the personal view (used by the "My time off" button for HR/admin). */
  personal?: boolean;
};

export function MyTimeOffPage({ personal = false }: MyTimeOffPageProps) {
  const { hasRole } = useAuth();

  // HR and admin manage other people's time off from the Leaves page: pick a
  // person, then see that person's balances. The personal view is still
  // available at /time-off/me so they can request their own leave.
  if (!personal && hasRole("admin", "hr")) {
    return <LeaveDirectory />;
  }

  return <MyLeavePanel />;
}

import type { ReactNode } from "react";
import type { Permission } from "../contracts/auth";
import { useAuth } from "../auth/AuthContext";

type Props = {
  permission: Permission;
  children: ReactNode;
  fallback?: ReactNode;
};

/** Boundary: hide privileged UI when role lacks permission. */
export function RequirePermission({ permission, children, fallback = null }: Props) {
  const { can } = useAuth();
  if (!can(permission)) return <>{fallback}</>;
  return <>{children}</>;
}

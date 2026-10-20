export type Role = "security_admin" | "analyst" | "viewer";

export type Permission =
  | "console:access"
  | "mempool:read"
  | "mempool:simulate"
  | "analytics:read"
  | "analytics:export"
  | "settings:read"
  | "settings:write"
  | "diagnostics:read"
  | "diagnostics:block";

export type AuthUser = {
  id: string;
  email: string;
  name: string;
  role: Role;
  initials: string;
  wallet: string;
  network: string;
};

export type Session = {
  user: AuthUser;
  accessToken: string;
  expiresAt: number;
};

export type LoginInput = { email: string; password: string };
export type SignupInput = { name: string; email: string; password: string };
export type WalletInput = { address: string };

export const ROLE_PERMISSIONS: Record<Role, readonly Permission[]> = {
  security_admin: [
    "console:access",
    "mempool:read",
    "mempool:simulate",
    "analytics:read",
    "analytics:export",
    "settings:read",
    "settings:write",
    "diagnostics:read",
    "diagnostics:block",
  ],
  analyst: [
    "console:access",
    "mempool:read",
    "mempool:simulate",
    "analytics:read",
    "analytics:export",
    "settings:read",
    "diagnostics:read",
    "diagnostics:block",
  ],
  viewer: [
    "console:access",
    "mempool:read",
    "analytics:read",
    "diagnostics:read",
  ],
} as const;

export function permissionsFor(role: Role): readonly Permission[] {
  return ROLE_PERMISSIONS[role];
}

export function hasPermission(role: Role, permission: Permission): boolean {
  return ROLE_PERMISSIONS[role].includes(permission);
}

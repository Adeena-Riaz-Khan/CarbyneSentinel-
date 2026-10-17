import { describe, expect, it } from "vitest";
import { hasPermission, ROLE_PERMISSIONS } from "../contracts/auth";

describe("RBAC matrix (BR-AUTH-2, BR-PERM-1)", () => {
  it("admin has freeze and settings write", () => {
    expect(hasPermission("security_admin", "agents:freeze")).toBe(true);
    expect(hasPermission("security_admin", "settings:write")).toBe(true);
  });

  it("analyst cannot freeze or write settings", () => {
    expect(hasPermission("analyst", "agents:freeze")).toBe(false);
    expect(hasPermission("analyst", "settings:write")).toBe(false);
    expect(hasPermission("analyst", "mempool:simulate")).toBe(true);
  });

  it("viewer is read-mostly", () => {
    expect(hasPermission("viewer", "mempool:simulate")).toBe(false);
    expect(hasPermission("viewer", "settings:read")).toBe(false);
    expect(hasPermission("viewer", "agents:read")).toBe(true);
  });

  it("every role includes console:access", () => {
    for (const role of Object.keys(ROLE_PERMISSIONS) as Array<keyof typeof ROLE_PERMISSIONS>) {
      expect(ROLE_PERMISSIONS[role]).toContain("console:access");
    }
  });
});

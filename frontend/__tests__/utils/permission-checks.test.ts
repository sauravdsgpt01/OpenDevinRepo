import { describe, expect, it } from "vitest";
import { getAvailableRolesAUserCanAssign } from "#/utils/org/permission-checks";
import { PermissionKey } from "#/utils/org/permissions";

describe("getAvailableRolesAUserCanAssign", () => {
    it("returns empty array if user has no permissions", () => {
        const result = getAvailableRolesAUserCanAssign([]);
        expect(result).toEqual([]);
    });

    it("returns only roles the user has permission for", () => {
        const userPermissions: PermissionKey[] = [
            "change_user_role:member",
            "change_user_role:admin",
        ];
        const result = getAvailableRolesAUserCanAssign(userPermissions);
        expect(result.sort()).toEqual(["admin", "member"].sort());
    });

    it("returns all roles if user has all permissions", () => {
        const allPermissions: PermissionKey[] = [
            "change_user_role:member",
            "change_user_role:admin",
            "change_user_role:owner",
        ];
        const result = getAvailableRolesAUserCanAssign(allPermissions);
        expect(result.sort()).toEqual(["member", "admin", "owner"].sort());
    });
});

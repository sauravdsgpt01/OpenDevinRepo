import { redirect } from "react-router";
import { getActiveOrganizationUser } from "./permission-checks";
import { PermissionKey, rolePermissions } from "./permissions";

/**
 * Creates a clientLoader guard that checks if the user has the required permission.
 * Redirects to the fallback path if permission is denied.
 *
 * @param requiredPermission - The permission key to check
 * @param redirectPath - The path to redirect to if permission denied (default: /settings/user)
 * @returns A clientLoader function that can be exported from route files
 */
export const createPermissionGuard =
  (
    requiredPermission: PermissionKey,
    redirectPath: string = "/settings/user",
  ) =>
  async () => {
    const user = await getActiveOrganizationUser();

    if (!user) {
      return redirect(redirectPath);
    }

    const userRole = user.role ?? "member";

    if (!rolePermissions[userRole].includes(requiredPermission)) {
      return redirect(redirectPath);
    }

    return null;
  };

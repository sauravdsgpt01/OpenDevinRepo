import { organizationService } from "#/api/organization-service/organization-service.api";
import { getSelectedOrganizationIdFromStore } from "#/stores/selected-organization-store";
import { OrganizationMember, OrganizationUserRole } from "#/types/org";
import { getMeFromQueryClient } from "../query-client-getters";
import { PermissionKey } from "./permissions";
import { queryClient } from "#/query-client-config";

/**
 * Get the active organization user.
 * Reads from cache first, fetches if missing.
 * @returns OrganizationMember
 */
export const getActiveOrganizationUser = async (): Promise<
  OrganizationMember | undefined
> => {
  const orgId = getSelectedOrganizationIdFromStore();
  if (!orgId) return undefined;
  let user = getMeFromQueryClient(orgId);
  if (!user) {
    user = await organizationService.getMe({ orgId });
    queryClient.setQueryData(["organizations", orgId, "me"], user);
  }
  return user;
};

/**
 * Get a list of roles that a user has permission to assign to other users
 * @param userPermissions all permission for active user
 * @returns an array of roles (strings) the user can change other users to
 */
export const getAvailableRolesAUserCanAssign = (
  userPermissions: PermissionKey[],
): OrganizationUserRole[] => {
  const availableRoles: OrganizationUserRole[] = [];
  if (userPermissions.includes("change_user_role:member")) {
    availableRoles.push("member");
  }
  if (userPermissions.includes("change_user_role:admin")) {
    availableRoles.push("admin");
  }
  if (userPermissions.includes("change_user_role:owner")) {
    availableRoles.push("owner");
  }
  return availableRoles;
};

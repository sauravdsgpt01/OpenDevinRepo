import { useConfig } from "#/hooks/query/use-config";
import {
  SAAS_NAV_ITEMS,
  OSS_NAV_ITEMS,
  SettingsNavItem,
} from "#/constants/settings-nav";
import { OrganizationUserRole } from "#/types/org";
import { isBillingHidden } from "#/utils/org/billing-visibility";
import { useSelectedOrganizationStore } from "#/stores/selected-organization-store";
import { useMe } from "./query/use-me";
import { usePermission } from "./organizations/use-permissions";

/**
 * Build Settings navigation items based on:
 * - app mode (saas / oss)
 * - feature flags
 * - active user's role
 * @returns Settings Nav Items []
 */
export function useSettingsNavItems(): SettingsNavItem[] {
  const { data: config } = useConfig();
  const { data: user } = useMe();
  const userRole: OrganizationUserRole = user?.role ?? "member";
  const { hasPermission } = usePermission(userRole);

  const { organizationId } = useSelectedOrganizationStore();

  const shouldHideLlmSettings = !!config?.FEATURE_FLAGS?.HIDE_LLM_SETTINGS;
  const shouldHideBilling = isBillingHidden(
    config,
    hasPermission("view_billing"),
  );
  const isSaasMode = config?.APP_MODE === "saas";

  let items = isSaasMode ? SAAS_NAV_ITEMS : OSS_NAV_ITEMS;

  if (shouldHideLlmSettings) {
    items = items.filter((item) => item.to !== "/settings");
  }

  if (shouldHideBilling) {
    items = items.filter((item) => item.to !== "/settings/billing");
  }

  if (!hasPermission("view_billing") || !organizationId) {
    items = items.filter((item) => item.to !== "/settings/org");
  }

  if (!hasPermission("invite_user_to_organization") || !organizationId) {
    items = items.filter((item) => item.to !== "/settings/org-members");
  }

  return items;
}

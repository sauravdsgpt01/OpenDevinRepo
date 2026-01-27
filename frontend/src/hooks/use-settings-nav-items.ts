import { useConfig } from "#/hooks/query/use-config";
import {
  SAAS_NAV_ITEMS,
  OSS_NAV_ITEMS,
  SettingsNavItem,
} from "#/constants/settings-nav";
import { OrganizationUserRole } from "#/types/org";
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

  const shouldHideLlmSettings = !!config?.FEATURE_FLAGS?.HIDE_LLM_SETTINGS;
  const shouldHideBilling =
    !!config?.FEATURE_FLAGS?.HIDE_BILLING || !hasPermission("view_billing");
  const isSaasMode = config?.APP_MODE === "saas";

  let items = isSaasMode ? SAAS_NAV_ITEMS : OSS_NAV_ITEMS;

  if (shouldHideLlmSettings) {
    items = items.filter((item) => item.to !== "/settings");
  }

  if (shouldHideBilling) {
    items = items.filter((item) => item.to !== "/settings/billing");
  }

  return items;
}

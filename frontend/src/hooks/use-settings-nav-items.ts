import { useConfig } from "#/hooks/query/use-config";
import { SAAS_NAV_ITEMS, OSS_NAV_ITEMS } from "#/constants/settings-nav";

export function useSettingsNavItems() {
  const { data: config } = useConfig();

  const shouldHideLlmSettings = !!config?.FEATURE_FLAGS?.HIDE_LLM_SETTINGS;
  const shouldHideBilling = !!config?.FEATURE_FLAGS?.HIDE_BILLING;
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

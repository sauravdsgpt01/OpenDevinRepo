import { describe, it, expect } from "vitest";
import { isBillingHidden } from "#/utils/org/billing-visibility";
import { GetConfigResponse } from "#/api/option-service/option.types";

describe("isBillingHidden", () => {
  const createConfig = (
    featureFlagOverrides: Partial<GetConfigResponse["FEATURE_FLAGS"]> = {},
  ): GetConfigResponse => ({
    APP_MODE: "saas",
    GITHUB_CLIENT_ID: "test",
    POSTHOG_CLIENT_KEY: "test",
    FEATURE_FLAGS: {
      ENABLE_BILLING: false,
      HIDE_LLM_SETTINGS: false,
      HIDE_BILLING: false,
      ENABLE_JIRA: false,
      ENABLE_JIRA_DC: false,
      ENABLE_LINEAR: false,
      ...featureFlagOverrides,
    },
  });

  it("should return true when config is undefined (safe default)", () => {
    expect(isBillingHidden(undefined, true)).toBe(true);
  });

  it("should return true when HIDE_BILLING feature flag is true", () => {
    const config = createConfig({ HIDE_BILLING: true });
    expect(isBillingHidden(config, true)).toBe(true);
  });

  it("should return true when user lacks view_billing permission", () => {
    const config = createConfig();
    expect(isBillingHidden(config, false)).toBe(true);
  });

  it("should return true when both HIDE_BILLING is true and user lacks permission", () => {
    const config = createConfig({ HIDE_BILLING: true });
    expect(isBillingHidden(config, false)).toBe(true);
  });

  it("should return false when HIDE_BILLING is false and user has view_billing permission", () => {
    const config = createConfig();
    expect(isBillingHidden(config, true)).toBe(false);
  });

  it("should treat absent HIDE_BILLING as false (billing visible, subject to permission)", () => {
    const config = createConfig({ HIDE_BILLING: false });
    expect(isBillingHidden(config, true)).toBe(false);
  });
});

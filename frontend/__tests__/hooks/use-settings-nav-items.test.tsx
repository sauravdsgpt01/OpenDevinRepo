import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { renderHook, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { SAAS_NAV_ITEMS, OSS_NAV_ITEMS } from "#/constants/settings-nav";
import OptionService from "#/api/option-service/option-service.api";
import { useSettingsNavItems } from "#/hooks/use-settings-nav-items";
import { OrganizationMember } from "#/types/org";
import { useSelectedOrganizationStore } from "#/stores/selected-organization-store";
import { organizationService } from "#/api/organization-service/organization-service.api";

const queryClient = new QueryClient();
const wrapper = ({ children }: { children: React.ReactNode }) => (
  <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
);

const mockConfig = (appMode: "saas" | "oss", hideLlmSettings = false) => {
  vi.spyOn(OptionService, "getConfig").mockResolvedValue({
    APP_MODE: appMode,
    FEATURE_FLAGS: { HIDE_LLM_SETTINGS: hideLlmSettings },
  } as Awaited<ReturnType<typeof OptionService.getConfig>>);
};

vi.mock("react-router", () => ({
  useRevalidator: () => ({ revalidate: vi.fn() }),
}));

const createMockUser = (
  overrides: Partial<OrganizationMember> = {},
): OrganizationMember => ({
  org_id: "org-1",
  user_id: "user-1",
  email: "test@example.com",
  role: "member",
  llm_api_key: "",
  max_iterations: 100,
  llm_model: "gpt-4",
  llm_api_key_for_byor: null,
  llm_base_url: "",
  status: "active",
  ...overrides,
});

const seedActiveUser = (user: Partial<OrganizationMember>) => {
  useSelectedOrganizationStore.setState({ organizationId: "org-1" });
  vi.spyOn(organizationService, "getMe").mockResolvedValue(
    createMockUser(user),
  );
};

describe("useSettingsNavItems", () => {
  beforeEach(() => {
    queryClient.clear();
    vi.restoreAllMocks();
  });

  it("should return SAAS_NAV_ITEMS when APP_MODE is 'saas' and userRole is 'member'", async () => {
    mockConfig("saas");
    seedActiveUser({ role: "member" });

    const { result } = renderHook(() => useSettingsNavItems(), { wrapper });

    await waitFor(() => {
      expect(result.current).toEqual(
        SAAS_NAV_ITEMS.filter(
          item => item.to !== "/settings/billing"
        ),
      );
    });
  });

  it("should return SAAS_NAV_ITEMS when APP_MODE is 'saas' and userRole is NOT 'member'", async () => {
    mockConfig("saas");
    seedActiveUser({ role: "admin" });
    const { result } = renderHook(() => useSettingsNavItems(), { wrapper });

    await waitFor(() => {
      expect(result.current).toEqual(SAAS_NAV_ITEMS);
    });
  });

  it("should return OSS_NAV_ITEMS when APP_MODE is 'oss'", async () => {
    mockConfig("oss");
    seedActiveUser({ role: "admin" });
    const { result } = renderHook(() => useSettingsNavItems(), { wrapper });

    await waitFor(() => {
      expect(result.current).toEqual(OSS_NAV_ITEMS);
    });
  });

  it("should filter out '/settings' item when HIDE_LLM_SETTINGS feature flag is enabled", async () => {
    mockConfig("saas", true);
    seedActiveUser({ role: "admin" });
    const { result } = renderHook(() => useSettingsNavItems(), { wrapper });

    await waitFor(() => {
      expect(
        result.current.find((item) => item.to === "/settings"),
      ).toBeUndefined();
    });
  });
});

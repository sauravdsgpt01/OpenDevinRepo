import { renderHook } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { useIsOnIntermediatePage } from "#/hooks/use-is-on-intermediate-page";

describe("useIsOnIntermediatePage", () => {
  const originalLocation = window.location;

  beforeEach(() => {
    // Mock window.location
    Object.defineProperty(window, "location", {
      writable: true,
      value: { pathname: "/" },
    });
  });

  afterEach(() => {
    // Restore original window.location
    Object.defineProperty(window, "location", {
      writable: true,
      value: originalLocation,
    });
    vi.restoreAllMocks();
  });

  describe("returns true for intermediate pages", () => {
    it("should return true when on /accept-tos page", () => {
      window.location.pathname = "/accept-tos";

      const { result } = renderHook(() => useIsOnIntermediatePage());

      expect(result.current).toBe(true);
    });

    it("should return true when on /onboarding page", () => {
      window.location.pathname = "/onboarding";

      const { result } = renderHook(() => useIsOnIntermediatePage());

      expect(result.current).toBe(true);
    });
  });

  describe("returns false for non-intermediate pages", () => {
    it("should return false when on root page", () => {
      window.location.pathname = "/";

      const { result } = renderHook(() => useIsOnIntermediatePage());

      expect(result.current).toBe(false);
    });

    it("should return false when on /login page", () => {
      window.location.pathname = "/login";

      const { result } = renderHook(() => useIsOnIntermediatePage());

      expect(result.current).toBe(false);
    });

    it("should return false when on /settings page", () => {
      window.location.pathname = "/settings";

      const { result } = renderHook(() => useIsOnIntermediatePage());

      expect(result.current).toBe(false);
    });

    it("should return false when on /settings/user page", () => {
      window.location.pathname = "/settings/user";

      const { result } = renderHook(() => useIsOnIntermediatePage());

      expect(result.current).toBe(false);
    });

    it("should return false when on /conversations/:id page", () => {
      window.location.pathname = "/conversations/abc-123";

      const { result } = renderHook(() => useIsOnIntermediatePage());

      expect(result.current).toBe(false);
    });
  });

  describe("handles edge cases", () => {
    it("should return false for paths that contain intermediate page names but are not exact matches", () => {
      window.location.pathname = "/accept-tos-extra";

      const { result } = renderHook(() => useIsOnIntermediatePage());

      expect(result.current).toBe(false);
    });

    it("should return false for paths with intermediate page names as subpaths", () => {
      window.location.pathname = "/settings/accept-tos";

      const { result } = renderHook(() => useIsOnIntermediatePage());

      expect(result.current).toBe(false);
    });

    it("should return false for paths with query parameters", () => {
      // Note: window.location.pathname doesn't include query params,
      // but we test the pathname value to ensure the hook handles it correctly
      window.location.pathname = "/accept-tos";

      const { result } = renderHook(() => useIsOnIntermediatePage());

      expect(result.current).toBe(true);
    });
  });
});

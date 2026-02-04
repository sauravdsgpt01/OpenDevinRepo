const INTERMEDIATE_PAGE_PATHS = ["/accept-tos", "/onboarding"];

/**
 * Checks if the current page is an intermediate page.
 *
 * This hook is reusable for all intermediate pages. To add a new intermediate page,
 * add its path to INTERMEDIATE_PAGE_PATHS array.
 *
 * Note: This hook uses window.location.pathname directly to avoid Router context
 * dependency issues in tests.
 *
 */
export const useIsOnIntermediatePage = (): boolean => {
  const pathname =
    typeof window !== "undefined" ? window.location.pathname : "/";

  return INTERMEDIATE_PAGE_PATHS.includes(
    pathname as (typeof INTERMEDIATE_PAGE_PATHS)[number],
  );
};

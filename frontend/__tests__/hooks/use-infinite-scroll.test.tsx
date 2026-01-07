import { render, screen, act } from "@testing-library/react";
import { expect, test, vi, beforeEach, afterEach } from "vitest";
import { useInfiniteScroll } from "#/hooks/use-infinite-scroll";

interface InfiniteScrollTestComponentProps {
  hasNextPage: boolean;
  isFetchingNextPage: boolean;
  fetchNextPage: () => void;
  threshold?: number;
}

function InfiniteScrollTestComponent({
  hasNextPage,
  isFetchingNextPage,
  fetchNextPage,
  threshold = 100,
}: InfiniteScrollTestComponentProps) {
  const { setRef } = useInfiniteScroll({
    hasNextPage,
    isFetchingNextPage,
    fetchNextPage,
    threshold,
  });

  return (
    <div
      data-testid="scroll-container"
      ref={setRef}
      style={{ height: "200px", overflow: "auto" }}
    >
      <div style={{ height: "1000px" }}>Scrollable content</div>
    </div>
  );
}

beforeEach(() => {
  // Mock scrollHeight, clientHeight, and scrollTop
  Object.defineProperty(HTMLElement.prototype, "scrollHeight", {
    configurable: true,
    get() {
      return 1000;
    },
  });
  Object.defineProperty(HTMLElement.prototype, "clientHeight", {
    configurable: true,
    get() {
      return 200;
    },
  });
});

afterEach(() => {
  vi.restoreAllMocks();
});

test("should call fetchNextPage when scrolled near bottom", async () => {
  const fetchNextPage = vi.fn();

  render(
    <InfiniteScrollTestComponent
      hasNextPage
      isFetchingNextPage={false}
      fetchNextPage={fetchNextPage}
      threshold={100}
    />,
  );

  const container = screen.getByTestId("scroll-container");

  // Simulate scrolling near the bottom (scrollTop + clientHeight + threshold >= scrollHeight)
  // scrollHeight = 1000, clientHeight = 200, threshold = 100
  // Need scrollTop >= 1000 - 200 - 100 = 700
  await act(async () => {
    Object.defineProperty(container, "scrollTop", {
      configurable: true,
      value: 750,
    });
    container.dispatchEvent(new Event("scroll"));
  });

  expect(fetchNextPage).toHaveBeenCalled();
});

test("should not call fetchNextPage when not scrolled near bottom", async () => {
  const fetchNextPage = vi.fn();

  render(
    <InfiniteScrollTestComponent
      hasNextPage
      isFetchingNextPage={false}
      fetchNextPage={fetchNextPage}
      threshold={100}
    />,
  );

  const container = screen.getByTestId("scroll-container");

  // Simulate scrolling but not near the bottom
  await act(async () => {
    Object.defineProperty(container, "scrollTop", {
      configurable: true,
      value: 100,
    });
    container.dispatchEvent(new Event("scroll"));
  });

  expect(fetchNextPage).not.toHaveBeenCalled();
});

test("should not call fetchNextPage when hasNextPage is false", async () => {
  const fetchNextPage = vi.fn();

  render(
    <InfiniteScrollTestComponent
      hasNextPage={false}
      isFetchingNextPage={false}
      fetchNextPage={fetchNextPage}
      threshold={100}
    />,
  );

  const container = screen.getByTestId("scroll-container");

  // Simulate scrolling near the bottom
  await act(async () => {
    Object.defineProperty(container, "scrollTop", {
      configurable: true,
      value: 750,
    });
    container.dispatchEvent(new Event("scroll"));
  });

  expect(fetchNextPage).not.toHaveBeenCalled();
});

test("should not call fetchNextPage when already fetching", async () => {
  const fetchNextPage = vi.fn();

  render(
    <InfiniteScrollTestComponent
      hasNextPage
      isFetchingNextPage
      fetchNextPage={fetchNextPage}
      threshold={100}
    />,
  );

  const container = screen.getByTestId("scroll-container");

  // Simulate scrolling near the bottom
  await act(async () => {
    Object.defineProperty(container, "scrollTop", {
      configurable: true,
      value: 750,
    });
    container.dispatchEvent(new Event("scroll"));
  });

  expect(fetchNextPage).not.toHaveBeenCalled();
});

test("should return a callback ref that can be assigned to elements", () => {
  const fetchNextPage = vi.fn();

  render(
    <InfiniteScrollTestComponent
      hasNextPage
      isFetchingNextPage={false}
      fetchNextPage={fetchNextPage}
    />,
  );

  const container = screen.getByTestId("scroll-container");
  expect(container).toBeInTheDocument();
});

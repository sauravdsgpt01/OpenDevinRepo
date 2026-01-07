import { useEffect, useCallback, useState } from "react";

interface UseInfiniteScrollOptions {
  hasNextPage: boolean;
  isFetchingNextPage: boolean;
  fetchNextPage: () => void;
  threshold?: number;
}

export const useInfiniteScroll = ({
  hasNextPage,
  isFetchingNextPage,
  fetchNextPage,
  threshold = 100,
}: UseInfiniteScrollOptions) => {
  const [container, setContainer] = useState<HTMLDivElement | null>(null);

  const handleScroll = useCallback(() => {
    if (!container || isFetchingNextPage || !hasNextPage) {
      return;
    }

    const { scrollTop, scrollHeight, clientHeight } = container;
    const isNearBottom = scrollTop + clientHeight >= scrollHeight - threshold;

    if (isNearBottom) {
      fetchNextPage();
    }
  }, [container, hasNextPage, isFetchingNextPage, fetchNextPage, threshold]);

  useEffect(() => {
    if (!container) return undefined;

    container.addEventListener("scroll", handleScroll);
    return () => {
      container.removeEventListener("scroll", handleScroll);
    };
  }, [container, handleScroll]);

  return { setRef: setContainer };
};

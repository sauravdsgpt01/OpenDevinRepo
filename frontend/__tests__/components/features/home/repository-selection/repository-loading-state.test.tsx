import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { RepositoryLoadingState } from "#/components/features/home/repository-selection/repository-loading-state";

describe("RepositoryLoadingState", () => {
  it("should render wrapper with correct testId", () => {
    render(<RepositoryLoadingState />);

    expect(screen.getByTestId("repo-dropdown-loading")).toBeInTheDocument();
  });

  it("should render spinner element inside the component", () => {
    render(<RepositoryLoadingState />);

    // The Spinner component renders with testId="spinner" by default
    expect(screen.getByTestId("spinner")).toBeInTheDocument();
  });

  it("should display translated loading text", () => {
    render(<RepositoryLoadingState />);

    // The mock translates keys to themselves
    expect(screen.getByText("HOME$LOADING_REPOSITORIES")).toBeInTheDocument();
  });

  it("should apply wrapper className when provided", () => {
    render(<RepositoryLoadingState wrapperClassName="custom-class" />);

    const wrapper = screen.getByTestId("repo-dropdown-loading");
    expect(wrapper).toHaveClass("custom-class");
  });

  it("should have default styling classes", () => {
    render(<RepositoryLoadingState />);

    const wrapper = screen.getByTestId("repo-dropdown-loading");
    expect(wrapper).toHaveClass("flex", "items-center", "gap-2");
  });
});

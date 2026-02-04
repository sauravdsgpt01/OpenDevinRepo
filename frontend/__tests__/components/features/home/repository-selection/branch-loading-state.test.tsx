import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { BranchLoadingState } from "#/components/features/home/repository-selection/branch-loading-state";

describe("BranchLoadingState", () => {
  it("should render spinner with correct testId", () => {
    render(<BranchLoadingState />);

    expect(screen.getByTestId("branch-dropdown-loading")).toBeInTheDocument();
  });

  it("should render spinner element inside the component", () => {
    render(<BranchLoadingState />);

    // The Spinner component renders with testId="spinner" by default
    expect(screen.getByTestId("spinner")).toBeInTheDocument();
  });

  it("should display translated loading text", () => {
    render(<BranchLoadingState />);

    // The mock translates keys to themselves
    expect(screen.getByText("HOME$LOADING_BRANCHES")).toBeInTheDocument();
  });

  it("should apply wrapper className when provided", () => {
    render(<BranchLoadingState wrapperClassName="custom-class" />);

    const wrapper = screen.getByTestId("branch-dropdown-loading");
    expect(wrapper).toHaveClass("custom-class");
  });

  it("should have default styling classes", () => {
    render(<BranchLoadingState />);

    const wrapper = screen.getByTestId("branch-dropdown-loading");
    expect(wrapper).toHaveClass("flex", "items-center", "gap-2");
  });
});

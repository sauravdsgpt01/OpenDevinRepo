import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { Spinner } from "#/components/shared/spinner";

describe("Spinner", () => {
  it("should render with default testId", () => {
    render(<Spinner />);

    expect(screen.getByTestId("spinner")).toBeInTheDocument();
  });

  it("should have animate-spin class for rotation animation", () => {
    render(<Spinner />);

    expect(screen.getByTestId("spinner")).toHaveClass("animate-spin");
  });

  it("should render with default size (md = w-6 h-6)", () => {
    render(<Spinner />);

    const spinner = screen.getByTestId("spinner");
    expect(spinner).toHaveClass("w-6", "h-6");
  });

  it("should render with sm size (w-4 h-4)", () => {
    render(<Spinner size="sm" />);

    const spinner = screen.getByTestId("spinner");
    expect(spinner).toHaveClass("w-4", "h-4");
  });

  it("should render with lg size (w-10 h-10)", () => {
    render(<Spinner size="lg" />);

    const spinner = screen.getByTestId("spinner");
    expect(spinner).toHaveClass("w-10", "h-10");
  });

  it("should render with xl size (w-16 h-16)", () => {
    render(<Spinner size="xl" />);

    const spinner = screen.getByTestId("spinner");
    expect(spinner).toHaveClass("w-16", "h-16");
  });

  it("should use custom testId when provided", () => {
    render(<Spinner testId="custom-spinner" />);

    expect(screen.getByTestId("custom-spinner")).toBeInTheDocument();
    expect(screen.queryByTestId("spinner")).not.toBeInTheDocument();
  });

  it("should apply custom className", () => {
    render(<Spinner className="text-white" />);

    expect(screen.getByTestId("spinner")).toHaveClass("text-white");
  });

  it("should render with label text when provided", () => {
    render(<Spinner label="Loading..." />);

    expect(screen.getByText("Loading...")).toBeInTheDocument();
  });

  it("should not render label when not provided", () => {
    render(<Spinner />);

    expect(screen.queryByText(/loading/i)).not.toBeInTheDocument();
  });

  it("should use border-based styling for circular spinner appearance", () => {
    render(<Spinner />);

    const spinner = screen.getByTestId("spinner");
    expect(spinner).toHaveClass("border-2", "rounded-full");
  });
});

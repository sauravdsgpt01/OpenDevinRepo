import { Spinner } from "#/components/shared/spinner";

export function AgentLoading() {
  return (
    <Spinner size="sm" testId="agent-loading-spinner" className="text-white" />
  );
}

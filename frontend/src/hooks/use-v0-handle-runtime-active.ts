/**
 * @deprecated V0 implementation - will be removed after full V1 migration.
 * This hook tracks runtime status for legacy V0 conversations only.
 */
import { RUNTIME_INACTIVE_STATES } from "#/types/agent-state";
import { useAgentStore } from "#/stores/agent-store";

export const useV0HandleRuntimeActive = () => {
  const { curAgentState } = useAgentStore();

  const runtimeActive = !RUNTIME_INACTIVE_STATES.includes(curAgentState);

  return { runtimeActive };
};

/**
 * @deprecated V0 implementation - will be removed after full V1 migration.
 * This wrapper handles events for legacy V0 conversations only.
 */
import React from "react";
import { useV0HandleWSEvents } from "#/hooks/use-v0-handle-ws-events";
import { useV0HandleRuntimeActive } from "#/hooks/use-v0-handle-runtime-active";

export function V0EventHandler({ children }: React.PropsWithChildren) {
  useV0HandleWSEvents();
  useV0HandleRuntimeActive();

  return children;
}

import React from "react";
import { OpenHandsEvent } from "#/types/v1/core";
import { isObservationEvent } from "#/types/v1/type-guards";
import { EventMessage } from "./event-message";
import { ChatMessage } from "../../features/chat/chat-message";
import { useOptimisticUserMessageStore } from "#/stores/optimistic-user-message-store";
import { usePlanPreviewEvents } from "./hooks/use-plan-preview-events";
// TODO: Implement microagent functionality for V1 when APIs support V1 event IDs
// import { AgentState } from "#/types/agent-state";
// import MemoryIcon from "#/icons/memory_icon.svg?react";

interface MessagesProps {
  messages: OpenHandsEvent[]; // UI events (actions replaced by observations)
  allEvents: OpenHandsEvent[]; // Full event history (for action lookup)
}

export const Messages: React.FC<MessagesProps> = React.memo(
  ({ messages, allEvents }) => {
    const { getOptimisticUserMessage } = useOptimisticUserMessageStore();

    const optimisticUserMessage = getOptimisticUserMessage();

    // Get the set of event IDs that should render PlanPreview
    // This ensures only one preview per user message "phase"
    const planPreviewEventIds = usePlanPreviewEvents(allEvents);

    // Find the last TaskTrackerObservation so only it shows a spinning icon
    const lastTaskTrackingIndex = React.useMemo(() => {
      for (let i = messages.length - 1; i >= 0; i -= 1) {
        const msg = messages[i];
        if (
          isObservationEvent(msg) &&
          msg.observation.kind === "TaskTrackerObservation"
        ) {
          return i;
        }
      }
      return -1;
    }, [messages]);

    // TODO: Implement microagent functionality for V1 if needed
    // For now, we'll skip microagent features

    return (
      <>
        {messages.map((message, index) => (
          <EventMessage
            key={message.id}
            event={message}
            messages={allEvents}
            isLastMessage={messages.length - 1 === index}
            isInLast10Actions={messages.length - 1 - index < 10}
            planPreviewEventIds={planPreviewEventIds}
            isLastTaskTrackingObservation={index === lastTaskTrackingIndex}
            // Microagent props - not implemented yet for V1
            // microagentStatus={undefined}
            // microagentConversationId={undefined}
            // microagentPRUrl={undefined}
            // actions={undefined}
          />
        ))}

        {optimisticUserMessage && (
          <ChatMessage type="user" message={optimisticUserMessage} />
        )}
      </>
    );
  },
  (prevProps, nextProps) => {
    // Prevent re-renders if messages are the same length
    if (prevProps.messages.length !== nextProps.messages.length) {
      return false;
    }

    return true;
  },
);

Messages.displayName = "Messages";

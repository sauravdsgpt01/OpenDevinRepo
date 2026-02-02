import { OpenHandsObservation } from "#/types/core/observations";
import { isTaskTrackingObservation } from "#/types/core/guards";
import { TaskTrackingObservationContent } from "../task-tracking-observation-content";
import { ConfirmationButtons } from "#/components/shared/buttons/confirmation-buttons";

interface TaskTrackingEventMessageProps {
  event: OpenHandsObservation;
  shouldShowConfirmationButtons: boolean;
  isLastTaskTrackingObservation?: boolean;
}

export function TaskTrackingEventMessage({
  event,
  shouldShowConfirmationButtons,
  isLastTaskTrackingObservation,
}: TaskTrackingEventMessageProps) {
  if (!isTaskTrackingObservation(event)) {
    return null;
  }

  return (
    <div>
      <TaskTrackingObservationContent
        event={event}
        isLatest={isLastTaskTrackingObservation}
      />
      {shouldShowConfirmationButtons && <ConfirmationButtons />}
    </div>
  );
}

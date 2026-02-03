import { useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "react-hot-toast";
import ConversationService from "#/api/conversation-service/conversation-service.api";
import { useEventStore } from "#/stores/use-event-store";
import { useConversationStore } from "#/stores/conversation-store";

export const useClearConversation = () => {
  const queryClient = useQueryClient();
  const { clearEvents } = useEventStore();
  const { clearAllFiles } = useConversationStore();

  return useMutation({
    mutationFn: (variables: { conversationId: string }) =>
      ConversationService.clearConversation(variables.conversationId),
    onSuccess: (data) => {
      // Check if the operation was successful
      if (data.status === "error") {
        toast.error(data.message);
        return;
      }

      // Clear local UI state
      clearEvents();
      clearAllFiles();

      // Show success message
      toast.success(`Cleared ${data.deleted_count} events`);

      // Invalidate relevant queries to refresh data
      queryClient.invalidateQueries({ queryKey: ["user", "conversations"] });
    },
    onError: (error) => {
      toast.error(
        error instanceof Error ? error.message : "Failed to clear conversation",
      );
    },
  });
};

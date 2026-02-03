import { useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "react-hot-toast";
import V1ConversationService from "#/api/conversation-service/v1-conversation-service.api";
import { Provider } from "#/types/settings";

interface UpdateConversationRepositoryVariables {
  conversationId: string;
  selectedRepository: string;
  selectedBranch?: string;
  gitProvider?: Provider;
}

export const useUpdateConversationRepository = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (variables: UpdateConversationRepositoryVariables) =>
      V1ConversationService.updateConversationRepository(
        variables.conversationId,
        variables.selectedRepository,
        variables.selectedBranch,
        variables.gitProvider,
      ),
    onSuccess: (data, variables) => {
      toast.success("Repository updated successfully");

      // Invalidate conversation queries to refresh data
      queryClient.invalidateQueries({
        queryKey: ["app-conversations", variables.conversationId],
      });
      queryClient.invalidateQueries({
        queryKey: ["user", "conversations"],
      });
    },
    onError: (error) => {
      toast.error(
        error instanceof Error ? error.message : "Failed to update repository",
      );
    },
  });
};

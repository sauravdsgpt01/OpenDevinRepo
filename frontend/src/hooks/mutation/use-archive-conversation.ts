import { useMutation, useQueryClient } from "@tanstack/react-query";
import ConversationService from "#/api/conversation-service/conversation-service.api";

export const useArchiveConversation = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (variables: { conversationId: string; archived: boolean }) =>
      ConversationService.updateConversation(variables.conversationId, {
        archived: variables.archived,
      }),
    onMutate: async (variables) => {
      await queryClient.cancelQueries({ queryKey: ["user", "conversations"] });
      const previousConversations = queryClient.getQueryData([
        "user",
        "conversations",
      ]);

      queryClient.setQueryData(
        ["user", "conversations"],
        (old: { conversation_id: string; archived?: boolean }[] | undefined) =>
          old?.map((conv) =>
            conv.conversation_id === variables.conversationId
              ? { ...conv, archived: variables.archived }
              : conv,
          ),
      );

      // Also optimistically update the active conversation query
      queryClient.setQueryData(
        ["user", "conversation", variables.conversationId],
        (old: { archived?: boolean } | undefined) =>
          old ? { ...old, archived: variables.archived } : old,
      );

      return { previousConversations };
    },
    onError: (err, variables, context) => {
      if (context?.previousConversations) {
        queryClient.setQueryData(
          ["user", "conversations"],
          context.previousConversations,
        );
      }
    },
    onSettled: (data, error, variables) => {
      // Invalidate and refetch the conversation list
      queryClient.invalidateQueries({
        queryKey: ["user", "conversations"],
      });

      // Also invalidate the specific conversation query
      queryClient.invalidateQueries({
        queryKey: ["user", "conversation", variables.conversationId],
      });
    },
  });
};

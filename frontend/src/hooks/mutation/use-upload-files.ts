/**
 * @deprecated V0 implementation - will be removed after full V1 migration.
 * Use `useV1UploadFiles` from `use-v1-upload-files.ts` instead.
 */
import { useMutation } from "@tanstack/react-query";
import ConversationService from "#/api/conversation-service/conversation-service.api";

export const useUploadFiles = () =>
  useMutation({
    mutationKey: ["upload-files"],
    mutationFn: (variables: { conversationId: string; files: File[] }) =>
      ConversationService.uploadFiles(
        variables.conversationId!,
        variables.files,
      ),
    onSuccess: async () => {},
    meta: {
      disableToast: true,
    },
  });

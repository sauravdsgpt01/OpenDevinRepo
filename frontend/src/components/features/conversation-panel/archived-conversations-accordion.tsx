import React from "react";
import { NavLink } from "react-router";
import { useTranslation } from "react-i18next";
import { Accordion, AccordionItem } from "@heroui/react";
import { I18nKey } from "#/i18n/declaration";
import { Conversation } from "#/api/open-hands.types";
import { Provider } from "#/types/settings";
import { ConversationCard } from "./conversation-card/conversation-card";
import FolderIcon from "#/icons/folder.svg?react";

interface ArchivedConversationsAccordionProps {
  conversations: Conversation[];
  onClose: () => void;
  onDelete: (conversationId: string, title: string) => void;
  onStop: (conversationId: string, version?: "V0" | "V1") => void;
  onChangeTitle: (conversationId: string, title: string) => void;
  onArchive: (conversationId: string, archived: boolean) => void;
  openContextMenuId: string | null;
  setOpenContextMenuId: (id: string | null) => void;
}

export function ArchivedConversationsAccordion({
  conversations,
  onClose,
  onDelete,
  onStop,
  onChangeTitle,
  onArchive,
  openContextMenuId,
  setOpenContextMenuId,
}: ArchivedConversationsAccordionProps) {
  const { t } = useTranslation();

  if (conversations.length === 0) {
    return null;
  }

  return (
    <Accordion
      variant="light"
      className="px-0"
      itemClasses={{
        base: "px-0",
        trigger:
          "px-3.5 py-3 cursor-pointer hover:bg-[#454545] data-[open=true]:bg-[#454545]",
        content: "p-0",
        indicator: "text-neutral-400",
        title: "text-neutral-400",
      }}
    >
      <AccordionItem
        key="archived"
        aria-label={t(I18nKey.CONVERSATION$ARCHIVED_CONVERSATIONS)}
        title={
          <div className="flex items-center gap-2">
            <FolderIcon width={16} height={16} className="text-neutral-400" />
            <span className="text-sm text-neutral-400">
              {t(I18nKey.CONVERSATION$ARCHIVED_CONVERSATIONS)} (
              {conversations.length})
            </span>
          </div>
        }
      >
        {conversations.map((project) => (
          <NavLink
            key={project.conversation_id}
            to={`/conversations/${project.conversation_id}`}
            onClick={onClose}
          >
            <ConversationCard
              onDelete={() => onDelete(project.conversation_id, project.title)}
              onStop={() =>
                onStop(project.conversation_id, project.conversation_version)
              }
              onChangeTitle={(title) =>
                onChangeTitle(project.conversation_id, title)
              }
              onArchive={() => onArchive(project.conversation_id, false)}
              isArchived
              title={project.title}
              selectedRepository={{
                selected_repository: project.selected_repository,
                selected_branch: project.selected_branch,
                git_provider: project.git_provider as Provider,
              }}
              lastUpdatedAt={project.last_updated_at}
              createdAt={project.created_at}
              conversationStatus={project.status}
              conversationId={project.conversation_id}
              conversationVersion={project.conversation_version}
              contextMenuOpen={openContextMenuId === project.conversation_id}
              onContextMenuToggle={(isOpen) =>
                setOpenContextMenuId(isOpen ? project.conversation_id : null)
              }
            />
          </NavLink>
        ))}
      </AccordionItem>
    </Accordion>
  );
}

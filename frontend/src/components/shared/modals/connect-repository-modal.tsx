import React from "react";
import { useTranslation } from "react-i18next";
import { I18nKey } from "#/i18n/declaration";
import { useUserProviders } from "#/hooks/use-user-providers";
import { useUpdateConversationRepository } from "#/hooks/mutation/use-update-conversation-repository";
import { GitRepoDropdown } from "#/components/features/home/git-repo-dropdown/git-repo-dropdown";
import { GitBranchDropdown } from "#/components/features/home/git-branch-dropdown/git-branch-dropdown";
import { GitProviderDropdown } from "#/components/features/home/git-provider-dropdown";
import { Provider } from "#/types/settings";
import { Branch, GitRepository } from "#/types/git";
import { ModalBackdrop } from "./modal-backdrop";
import { ModalBody } from "./modal-body";
import { ModalButton } from "../buttons/modal-button";
import { useHomeStore } from "#/stores/home-store";

interface ConnectRepositoryModalProps {
  conversationId: string;
  onClose: () => void;
}

export function ConnectRepositoryModal({
  conversationId,
  onClose,
}: ConnectRepositoryModalProps) {
  const { t } = useTranslation();
  const { providers, isLoadingSettings } = useUserProviders();
  const { mutate: updateRepository, isPending } =
    useUpdateConversationRepository();
  const { setLastSelectedProvider, getLastSelectedProvider } = useHomeStore();

  const [selectedProvider, setSelectedProvider] =
    React.useState<Provider | null>(null);
  const [selectedRepository, setSelectedRepository] =
    React.useState<GitRepository | null>(null);
  const [selectedBranch, setSelectedBranch] = React.useState<Branch | null>(
    null,
  );

  // Auto-select provider logic (same as dashboard)
  React.useEffect(() => {
    if (providers.length === 0) return;

    // If there's only one provider, auto-select it
    if (providers.length === 1 && !selectedProvider) {
      setSelectedProvider(providers[0]);
      return;
    }

    // If there are multiple providers and none is selected, try to use the last selected one
    if (providers.length > 1 && !selectedProvider) {
      const lastSelected = getLastSelectedProvider();
      if (lastSelected && providers.includes(lastSelected)) {
        setSelectedProvider(lastSelected);
      }
    }
  }, [providers, selectedProvider, getLastSelectedProvider]);

  const handleProviderChange = (provider: Provider | null) => {
    if (provider === selectedProvider) {
      return;
    }
    setSelectedProvider(provider);
    setLastSelectedProvider(provider);
    setSelectedRepository(null);
    setSelectedBranch(null);
  };

  const handleRepoChange = (repository?: GitRepository) => {
    if (repository) {
      setSelectedRepository(repository);
      setSelectedBranch(null);
    } else {
      setSelectedRepository(null);
      setSelectedBranch(null);
    }
  };

  const handleBranchChange = React.useCallback((branch: Branch | null) => {
    setSelectedBranch(branch);
  }, []);

  const handleSave = () => {
    if (!selectedRepository || !selectedBranch || !conversationId) return;

    updateRepository(
      {
        conversationId,
        selectedRepository: selectedRepository.full_name,
        selectedBranch: selectedBranch.name,
        gitProvider: selectedProvider || undefined,
      },
      {
        onSuccess: () => {
          onClose();
        },
      },
    );
  };

  const canSave =
    selectedRepository && selectedBranch && !isPending && conversationId;

  return (
    <ModalBackdrop onClose={onClose}>
      <ModalBody testID="connect-repository-modal" width="small">
        <div className="flex flex-col gap-2 self-start w-full">
          <span className="text-xl leading-6 -tracking-[0.01em] font-semibold">
            {t(I18nKey.CONVERSATION$CHANGE_REPOSITORY)}
          </span>
          <span className="text-xs text-[#A3A3A3]">
            {t(I18nKey.HOME$SELECT_OR_INSERT_URL)}
          </span>
        </div>

        <div className="flex flex-col gap-4 w-full">
          {/* Provider dropdown - only show if multiple providers */}
          {providers.length > 1 && (
            <div className="flex flex-col gap-1">
              <label className="text-xs text-[#A3A3A3]">
                {t(I18nKey.CONVERSATION$GIT_PROVIDER)}
              </label>
              <GitProviderDropdown
                providers={providers}
                value={selectedProvider}
                placeholder="Select Provider"
                className="w-full"
                onChange={handleProviderChange}
                disabled={isLoadingSettings || isPending}
              />
            </div>
          )}

          {/* Repository dropdown */}
          <div className="flex flex-col gap-1">
            <label className="text-xs text-[#A3A3A3]">
              {t(I18nKey.CONVERSATION$REPOSITORY)}
            </label>
            <GitRepoDropdown
              provider={selectedProvider || providers[0]}
              value={selectedRepository?.id || null}
              repositoryName={selectedRepository?.full_name || null}
              placeholder="user/repo"
              disabled={!selectedProvider || isLoadingSettings || isPending}
              onChange={handleRepoChange}
              className="w-full"
            />
          </div>

          {/* Branch dropdown */}
          <div className="flex flex-col gap-1">
            <label className="text-xs text-[#A3A3A3]">
              {t(I18nKey.CONVERSATION$BRANCH)}
            </label>
            <GitBranchDropdown
              repository={selectedRepository?.full_name || null}
              provider={selectedProvider || providers[0]}
              selectedBranch={selectedBranch}
              onBranchSelect={handleBranchChange}
              defaultBranch={selectedRepository?.main_branch || null}
              placeholder="Select branch..."
              className="w-full"
              disabled={!selectedRepository || isLoadingSettings || isPending}
            />
          </div>
        </div>

        <div className="flex flex-col gap-2 w-full">
          <ModalButton
            onClick={handleSave}
            disabled={!canSave}
            text={isPending ? t(I18nKey.HOME$LOADING) : t(I18nKey.BUTTON$SAVE)}
            className="bg-[#4B6BFB] hover:bg-[#3B5BEB] disabled:bg-[#4B6BFB]/50 disabled:cursor-not-allowed"
          />
          <ModalButton
            onClick={onClose}
            disabled={isPending}
            text={t(I18nKey.BUTTON$CANCEL)}
            className="bg-transparent border border-[#525252] hover:bg-[#454545]"
          />
        </div>
      </ModalBody>
    </ModalBackdrop>
  );
}

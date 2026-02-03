import { useTranslation } from "react-i18next";
import { constructRepositoryUrl, cn } from "#/utils/utils";
import { Provider } from "#/types/settings";
import { I18nKey } from "#/i18n/declaration";
import { GitProviderIcon } from "#/components/shared/git-provider-icon";
import { GitExternalLinkIcon } from "./git-external-link-icon";
import RepoForkedIcon from "#/icons/repo-forked.svg?react";
import PlusIcon from "#/icons/u-plus.svg?react";
import EditIcon from "#/icons/u-edit.svg?react";

interface GitControlBarRepoButtonProps {
  selectedRepository: string | null | undefined;
  gitProvider: Provider | null | undefined;
  onConnectRepository?: () => void;
  onChangeRepository?: () => void;
}

export function GitControlBarRepoButton({
  selectedRepository,
  gitProvider,
  onConnectRepository,
  onChangeRepository,
}: GitControlBarRepoButtonProps) {
  const { t } = useTranslation();

  // Check if repository is truly connected (need both repo name AND provider)
  const hasRepository = !!(selectedRepository && gitProvider);

  const repositoryUrl = hasRepository
    ? constructRepositoryUrl(gitProvider, selectedRepository)
    : undefined;

  const buttonText = hasRepository
    ? selectedRepository
    : t(I18nKey.COMMON$NO_REPO_CONNECTED);

  // When repository is connected, show link to repository with change button
  if (hasRepository) {
    return (
      <div className="flex flex-row items-center gap-1">
        <a
          href={repositoryUrl}
          target="_blank"
          rel="noopener noreferrer"
          className={cn(
            "group flex flex-row items-center justify-between gap-2 pl-2.5 pr-2.5 py-1 rounded-[100px] flex-1 truncate relative",
            "border border-[#525252] bg-transparent hover:border-[#454545] cursor-pointer",
          )}
        >
          <div className="w-3 h-3 flex items-center justify-center flex-shrink-0">
            <GitProviderIcon
              gitProvider={gitProvider as Provider}
              className="w-3 h-3 inline-flex"
            />
          </div>
          <div
            className="font-normal text-white text-sm leading-5 truncate flex-1 min-w-0"
            title={buttonText}
          >
            {buttonText}
          </div>
          <GitExternalLinkIcon />
        </a>
        {onChangeRepository && (
          <button
            type="button"
            onClick={onChangeRepository}
            title={t(I18nKey.CONVERSATION$CHANGE_REPOSITORY)}
            className={cn(
              "flex items-center justify-center p-1.5 rounded-full",
              "border border-[#525252] bg-transparent hover:border-[#454545] hover:bg-[#454545]/30 cursor-pointer",
            )}
          >
            <EditIcon width={12} height={12} className="text-white" />
          </button>
        )}
      </div>
    );
  }

  // When no repository is connected, show clickable button to connect
  if (onConnectRepository) {
    return (
      <button
        type="button"
        onClick={onConnectRepository}
        className={cn(
          "group flex flex-row items-center justify-between gap-2 pl-2.5 pr-2.5 py-1 rounded-[100px] flex-1 truncate relative",
          "border border-[#525252] bg-transparent hover:border-[#454545] hover:bg-[#454545]/30 cursor-pointer min-w-[170px]",
        )}
      >
        <div className="w-3 h-3 flex items-center justify-center flex-shrink-0">
          <RepoForkedIcon width={12} height={12} color="white" />
        </div>
        <div
          className="font-normal text-white text-sm leading-5 truncate flex-1 min-w-0"
          title={buttonText}
        >
          {buttonText}
        </div>
        <PlusIcon width={12} height={12} className="text-white" />
      </button>
    );
  }

  // Fallback: no repository and no handler - show disabled state
  return (
    <div
      className={cn(
        "group flex flex-row items-center justify-between gap-2 pl-2.5 pr-2.5 py-1 rounded-[100px] flex-1 truncate relative",
        "border border-[rgba(71,74,84,0.50)] bg-transparent cursor-not-allowed min-w-[170px]",
      )}
    >
      <div className="w-3 h-3 flex items-center justify-center flex-shrink-0">
        <RepoForkedIcon width={12} height={12} color="white" />
      </div>
      <div
        className="font-normal text-white text-sm leading-5 truncate flex-1 min-w-0"
        title={buttonText}
      >
        {buttonText}
      </div>
    </div>
  );
}

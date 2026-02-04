import React from "react";
import { useTranslation } from "react-i18next";
import { IoClose, IoChevronDown, IoChevronForward } from "react-icons/io5";
import { ModalBackdrop } from "#/components/shared/modals/modal-backdrop";
import { BrandButton } from "#/components/features/settings/brand-button";
import { I18nKey } from "#/i18n/declaration";
import { PluginSpec } from "#/api/conversation-service/v1-conversation-service.types";
import { cn } from "#/utils/utils";

interface PluginLaunchModalProps {
  plugins: PluginSpec[];
  message?: string;
  isLoading?: boolean;
  onStartConversation: (plugins: PluginSpec[], initialMessage?: string) => void;
  onClose: () => void;
}

interface ExpandedState {
  [key: number]: boolean;
}

export function PluginLaunchModal({
  plugins,
  message,
  isLoading = false,
  onStartConversation,
  onClose,
}: PluginLaunchModalProps) {
  const { t } = useTranslation();
  const [pluginConfigs, setPluginConfigs] =
    React.useState<PluginSpec[]>(plugins);
  const [expandedSections, setExpandedSections] = React.useState<ExpandedState>(
    () => {
      // Initially expand plugins that have parameters
      const initial: ExpandedState = {};
      plugins.forEach((plugin, index) => {
        if (plugin.parameters && Object.keys(plugin.parameters).length > 0) {
          initial[index] = true;
        }
      });
      return initial;
    },
  );

  const pluginsWithParams = pluginConfigs.filter(
    (p) => p.parameters && Object.keys(p.parameters).length > 0,
  );
  const pluginsWithoutParams = pluginConfigs.filter(
    (p) => !p.parameters || Object.keys(p.parameters).length === 0,
  );

  const toggleSection = (index: number) => {
    setExpandedSections((prev) => ({
      ...prev,
      [index]: !prev[index],
    }));
  };

  const updateParameter = (
    pluginIndex: number,
    paramKey: string,
    value: unknown,
  ) => {
    setPluginConfigs((prev) => {
      const updated = [...prev];
      const plugin = { ...updated[pluginIndex] };
      plugin.parameters = {
        ...plugin.parameters,
        [paramKey]: value,
      };
      updated[pluginIndex] = plugin;
      return updated;
    });
  };

  const getPluginDisplayName = (plugin: PluginSpec): string => {
    const { source, repo_path: repoPath } = plugin;

    // If repo_path is specified, show the plugin name from the path
    if (repoPath) {
      const pathParts = repoPath.split("/");
      const pluginName = pathParts[pathParts.length - 1];
      return pluginName;
    }

    // Otherwise show the repo name
    if (source.startsWith("github:")) {
      return source.replace("github:", "");
    }
    if (source.includes("/")) {
      const parts = source.split("/");
      return parts[parts.length - 1].replace(".git", "");
    }
    return source;
  };

  const getPluginSourceInfo = (plugin: PluginSpec): string => {
    const { source } = plugin;
    if (source.startsWith("github:")) {
      return source.replace("github:", "");
    }
    if (source.includes("github.com/")) {
      return source.split("github.com/")[1]?.replace(".git", "") || source;
    }
    return source;
  };

  const handleStartConversation = () => {
    onStartConversation(pluginConfigs, message);
  };

  const renderParameterInput = (
    pluginIndex: number,
    paramKey: string,
    paramValue: unknown,
  ) => {
    const inputId = `plugin-${pluginIndex}-param-${paramKey}`;
    const inputClasses =
      "rounded-md border border-tertiary bg-base-secondary px-3 py-2 text-sm focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary";

    if (typeof paramValue === "boolean") {
      return (
        <div key={paramKey} className="flex items-center gap-3 py-2">
          <input
            id={inputId}
            data-testid={inputId}
            type="checkbox"
            checked={paramValue}
            onChange={(e) =>
              updateParameter(pluginIndex, paramKey, e.target.checked)
            }
            className="h-4 w-4 rounded border-tertiary bg-base-secondary accent-primary"
          />
          <label htmlFor={inputId} className="text-sm">
            {paramKey}
          </label>
        </div>
      );
    }

    if (typeof paramValue === "number") {
      return (
        <div key={paramKey} className="flex flex-col gap-1 py-2">
          <label htmlFor={inputId} className="text-sm text-tertiary">
            {paramKey}
          </label>
          <input
            id={inputId}
            data-testid={inputId}
            type="number"
            value={paramValue}
            onChange={(e) =>
              updateParameter(
                pluginIndex,
                paramKey,
                parseFloat(e.target.value) || 0,
              )
            }
            className={inputClasses}
          />
        </div>
      );
    }

    // Default: string input
    return (
      <div key={paramKey} className="flex flex-col gap-1 py-2">
        <label htmlFor={inputId} className="text-sm text-tertiary">
          {paramKey}
        </label>
        <input
          id={inputId}
          data-testid={inputId}
          type="text"
          value={String(paramValue ?? "")}
          onChange={(e) =>
            updateParameter(pluginIndex, paramKey, e.target.value)
          }
          className={inputClasses}
        />
      </div>
    );
  };

  const renderPluginSection = (plugin: PluginSpec, originalIndex: number) => {
    const isExpanded = expandedSections[originalIndex];
    const hasParams =
      plugin.parameters && Object.keys(plugin.parameters).length > 0;

    if (!hasParams) {
      return null;
    }

    return (
      <div
        key={`plugin-${originalIndex}`}
        className="rounded-lg border border-tertiary bg-tertiary"
      >
        <button
          type="button"
          onClick={() => toggleSection(originalIndex)}
          className="flex w-full items-center justify-between px-4 py-3 text-left hover:bg-base-tertiary rounded-t-lg"
          data-testid={`plugin-section-${originalIndex}`}
        >
          <span className="font-medium">{getPluginDisplayName(plugin)}</span>
          {isExpanded ? (
            <IoChevronDown className="h-5 w-5 text-tertiary" />
          ) : (
            <IoChevronForward className="h-5 w-5 text-tertiary" />
          )}
        </button>

        {isExpanded && (
          <div className="border-t border-tertiary px-4 py-3">
            {plugin.ref && (
              <div className="mb-2 text-xs text-tertiary">
                {t(I18nKey.LAUNCH$PLUGIN_REF)} {plugin.ref}
              </div>
            )}
            {plugin.repo_path && (
              <div className="mb-2 text-xs text-tertiary">
                {t(I18nKey.LAUNCH$PLUGIN_PATH)} {plugin.repo_path}
              </div>
            )}
            <div className="space-y-1">
              {Object.entries(plugin.parameters || {}).map(([key, value]) =>
                renderParameterInput(originalIndex, key, value),
              )}
            </div>
          </div>
        )}
      </div>
    );
  };

  const modalTitle =
    pluginConfigs.length === 1
      ? getPluginDisplayName(pluginConfigs[0])
      : t(I18nKey.LAUNCH$MODAL_TITLE_GENERIC);

  return (
    <ModalBackdrop onClose={onClose}>
      <div
        data-testid="plugin-launch-modal"
        className="bg-base-secondary p-6 rounded-xl flex flex-col gap-4 border border-tertiary w-[500px] max-w-[90vw] max-h-[80vh]"
      >
        <div className="flex w-full items-center justify-between">
          <h2 className="text-xl font-semibold">
            {t(I18nKey.LAUNCH$MODAL_TITLE)} {modalTitle}
          </h2>
          <button
            type="button"
            onClick={onClose}
            className="rounded-md p-1 text-tertiary hover:text-secondary hover:bg-tertiary"
            aria-label="Close"
            data-testid="close-button"
          >
            <IoClose className="h-5 w-5" />
          </button>
        </div>

        {message && <p className="text-sm text-tertiary">{message}</p>}

        <div className="flex-1 overflow-y-auto custom-scrollbar">
          {pluginsWithParams.length > 0 && (
            <div className="space-y-3">
              {pluginConfigs.map((plugin, index) =>
                renderPluginSection(plugin, index),
              )}
            </div>
          )}

          {pluginsWithoutParams.length > 0 && (
            <div className={cn(pluginsWithParams.length > 0 && "mt-4")}>
              <h3 className="mb-2 text-sm font-medium text-tertiary">
                {pluginsWithParams.length > 0
                  ? t(I18nKey.LAUNCH$ADDITIONAL_PLUGINS)
                  : t(I18nKey.LAUNCH$PLUGINS)}
              </h3>
              <div className="space-y-2">
                {pluginsWithoutParams.map((plugin, index) => (
                  <div
                    key={`simple-plugin-${index}`}
                    className="rounded-md bg-tertiary px-3 py-2 text-sm"
                  >
                    <div className="font-medium">
                      {getPluginDisplayName(plugin)}
                    </div>
                    <div className="text-xs text-tertiary mt-1">
                      {getPluginSourceInfo(plugin)}
                      {plugin.repo_path && (
                        <span className="ml-1">/ {plugin.repo_path}</span>
                      )}
                      {plugin.ref && (
                        <span className="ml-2">@ {plugin.ref}</span>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        <div className="flex w-full justify-end gap-2 pt-4 border-t border-tertiary">
          <BrandButton
            testId="start-conversation-button"
            type="button"
            variant="primary"
            onClick={handleStartConversation}
            isDisabled={isLoading}
            className="px-4"
          >
            {isLoading
              ? t(I18nKey.LAUNCH$STARTING)
              : t(I18nKey.LAUNCH$START_CONVERSATION)}
          </BrandButton>
        </div>
      </div>
    </ModalBackdrop>
  );
}

import { useState, useCallback, useMemo } from "react";
import { SlashCommand, filterCommands } from "#/config/slash-commands";

export interface UseSlashCommandsReturn {
  isMenuOpen: boolean;
  filteredCommands: SlashCommand[];
  selectedIndex: number;
  inputValue: string;
  setInputValue: (value: string) => void;
  handleInputChange: (text: string) => void;
  handleKeyDown: (e: React.KeyboardEvent) => SlashCommand | null;
  selectCommand: (command: SlashCommand) => void;
  closeMenu: () => void;
  resetState: () => void;
}

export function useSlashCommands(): UseSlashCommandsReturn {
  const [isMenuOpen, setIsMenuOpen] = useState(false);
  const [inputValue, setInputValue] = useState("");
  const [selectedIndex, setSelectedIndex] = useState(0);

  const filteredCommands = useMemo(() => {
    if (!inputValue.startsWith("/")) return [];
    return filterCommands(inputValue);
  }, [inputValue]);

  const handleInputChange = useCallback((text: string) => {
    setInputValue(text);

    if (text.startsWith("/")) {
      setIsMenuOpen(true);
      setSelectedIndex(0);
    } else {
      setIsMenuOpen(false);
      setSelectedIndex(0);
    }
  }, []);

  const selectCommand = useCallback((command: SlashCommand) => {
    setInputValue(command.name);
    setIsMenuOpen(false);
    setSelectedIndex(0);
  }, []);

  const closeMenu = useCallback(() => {
    setIsMenuOpen(false);
    setSelectedIndex(0);
  }, []);

  const resetState = useCallback(() => {
    setInputValue("");
    setIsMenuOpen(false);
    setSelectedIndex(0);
  }, []);

  // Handle keyboard navigation - returns selected command if Enter is pressed
  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent): SlashCommand | null => {
      // Don't handle if menu is closed or no commands available
      // Also check inputValue to handle race conditions with state updates
      if (
        !isMenuOpen ||
        filteredCommands.length === 0 ||
        !inputValue.startsWith("/")
      ) {
        return null;
      }

      if (e.key === "ArrowDown") {
        e.preventDefault();
        setSelectedIndex((prev) =>
          prev < filteredCommands.length - 1 ? prev + 1 : 0,
        );
        return null;
      }

      if (e.key === "ArrowUp") {
        e.preventDefault();
        setSelectedIndex((prev) =>
          prev > 0 ? prev - 1 : filteredCommands.length - 1,
        );
        return null;
      }

      if (e.key === "Enter") {
        e.preventDefault();
        const selectedCommand = filteredCommands[selectedIndex];
        if (selectedCommand) {
          selectCommand(selectedCommand);
          return selectedCommand;
        }
        return null;
      }

      if (e.key === "Escape") {
        e.preventDefault();
        closeMenu();
        return null;
      }

      if (e.key === "Tab") {
        e.preventDefault();
        const tabSelectedCommand = filteredCommands[selectedIndex];
        if (tabSelectedCommand) {
          selectCommand(tabSelectedCommand);
        }
        return null;
      }

      return null;
    },
    [
      isMenuOpen,
      filteredCommands,
      selectedIndex,
      selectCommand,
      closeMenu,
      inputValue,
    ],
  );

  return {
    isMenuOpen,
    filteredCommands,
    selectedIndex,
    inputValue,
    setInputValue,
    handleInputChange,
    handleKeyDown,
    selectCommand,
    closeMenu,
    resetState,
  };
}

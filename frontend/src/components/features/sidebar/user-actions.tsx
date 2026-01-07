import React from "react";
import { UserAvatar } from "./user-avatar";
import { AccountSettingsContextMenu } from "../context-menu/account-settings-context-menu";
import { useShouldShowUserFeatures } from "#/hooks/use-should-show-user-features";
import { cn } from "#/utils/utils";
import { useConfig } from "#/hooks/query/use-config";

interface UserActionsProps {
  onLogout: () => void;
  user?: { avatar_url: string };
  isLoading?: boolean;
}

export function UserActions({ onLogout, user, isLoading }: UserActionsProps) {
  const [accountContextMenuIsVisible, setAccountContextMenuIsVisible] =
    React.useState(false);

  const { data: config } = useConfig();

  // Use the shared hook to determine if user actions should be shown
  const shouldShowUserActions = useShouldShowUserFeatures();

  const toggleAccountMenu = () => {
    // Always toggle the menu, even if user is undefined
    setAccountContextMenuIsVisible((prev) => !prev);
  };

  const closeAccountMenu = () => {
    if (accountContextMenuIsVisible) {
      setAccountContextMenuIsVisible(false);
    }
  };

  const handleLogout = () => {
    onLogout();
    closeAccountMenu();
  };

  const isOSS = config?.APP_MODE === "oss";

  // Show the menu based on the new logic
  const showMenu =
    accountContextMenuIsVisible && (shouldShowUserActions || isOSS);

  return (
    <div
      data-testid="user-actions"
      className="w-8 h-8 relative cursor-pointer group"
    >
      <UserAvatar
        avatarUrl={user?.avatar_url}
        onClick={toggleAccountMenu}
        isLoading={isLoading}
      />

      {(shouldShowUserActions || isOSS) && (
        <div
          className={cn(
            // Position absolutely to avoid overlapping with the avatar button
            "absolute top-full left-0",
            // Show on hover but only enable pointer events when menu is open via click
            // This prevents the menu from intercepting clicks on the avatar
            "opacity-0 pointer-events-none group-hover:opacity-100",
            showMenu && "opacity-100 pointer-events-auto",
            // Invisible hover bridge: extends hover zone to create a "safe corridor"
            // for diagonal mouse movement to the menu (only active when menu is visible)
            showMenu &&
              "before:absolute before:bottom-0 before:right-0 before:w-[200px] before:h-[300px]",
          )}
        >
          <AccountSettingsContextMenu
            onLogout={handleLogout}
            onClose={closeAccountMenu}
          />
        </div>
      )}
    </div>
  );
}

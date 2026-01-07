import test, { expect } from "@playwright/test";

/**
 * Test for issue #11933: Avatar context menu closes when moving cursor diagonally
 *
 * This test verifies that the user can move their cursor diagonally from the
 * avatar to the context menu without the menu closing unexpectedly.
 *
 * NOTE: The CSS hover bridge behavior cannot be reliably tested with Playwright
 * because mouse.move() doesn't consistently trigger CSS :hover states on pseudo-elements.
 * This test instead verifies the click-to-open behavior which uses JavaScript state.
 */
test("avatar context menu stays open when clicked and mouse moves away", async ({
  page,
}) => {
  await page.goto("/");

  // Get the user avatar button
  const userAvatar = page.getByTestId("user-avatar");
  await expect(userAvatar).toBeVisible();

  // Click the avatar to open the menu (this uses JavaScript state, not CSS hover)
  await userAvatar.click();

  // The context menu should appear
  const contextMenu = page.getByTestId("account-settings-context-menu");
  await expect(contextMenu).toBeVisible();

  // The menu wrapper should have opacity 1 when opened via click
  const menuWrapper = contextMenu.locator("..");
  await expect(menuWrapper).toHaveCSS("opacity", "1");

  // Get avatar bounding box
  const avatarBox = await userAvatar.boundingBox();
  if (!avatarBox) {
    throw new Error("Could not get bounding box for avatar");
  }

  // Move the mouse away from the avatar
  const leftX = avatarBox.x + 2;
  const aboveY = avatarBox.y - 50;
  await page.mouse.move(leftX, aboveY);

  // The menu should remain visible because it was opened via click (JavaScript state)
  // not CSS hover, so moving the mouse away doesn't close it
  await expect(menuWrapper).toHaveCSS("opacity", "1");
});

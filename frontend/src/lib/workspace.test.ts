import { describe, expect, test } from "bun:test";

import { buildWorkspaceContent } from "./workspace";

describe("buildWorkspaceContent", () => {
  test("returns a dashboard-specific title and inspector label", () => {
    const content = buildWorkspaceContent("Dashboard");

    expect(content.headerTitle).toBe("Dashboard");
    expect(content.keyboardTitle).toBe("Workspace");
    expect(content.selectionLabel).toBe("Overview");
  });

  test("returns a distinct keymap view", () => {
    const content = buildWorkspaceContent("Keymap");

    expect(content.headerTitle).toBe("Keymap");
    expect(content.keyboardTitle).toBe("Base Layer");
    expect(content.selectionLabel).toBe("Editing: Right Option");
  });
});

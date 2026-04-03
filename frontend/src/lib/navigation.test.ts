import { describe, expect, test } from "bun:test";

import { defaultScreen, primaryNavigation } from "./navigation";

describe("navigation model", () => {
  test("defaults to the dashboard screen", () => {
    expect(defaultScreen).toBe("Dashboard");
  });

  test("matches the familiar launcher section order", () => {
    expect(primaryNavigation).toEqual([
      "Dashboard",
      "Device",
      "Keymap",
      "Lighting",
      "Macros",
      "Profiles",
      "Events",
      "Settings",
    ]);
  });
});

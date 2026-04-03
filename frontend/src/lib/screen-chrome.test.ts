import { describe, expect, test } from "bun:test";

import { buildHeaderChips, shouldShowDeviceCard } from "./screen-chrome";

describe("screen chrome", () => {
  test("lighting top bar keeps only profile and connection state", () => {
    expect(
      buildHeaderChips("Lighting", {
        activeProfile: "Profile 1",
        connectionLabel: "Connected",
        firmware: "BYT-0x010C-preview",
        syncState: "Live session",
      }),
    ).toEqual(["Profile 1", "Connected"]);
  });

  test("lighting hides the device card while dashboard keeps it", () => {
    expect(shouldShowDeviceCard("Lighting")).toBe(false);
    expect(shouldShowDeviceCard("Dashboard")).toBe(false);
    expect(shouldShowDeviceCard("Device")).toBe(true);
  });
});

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
    ).toEqual([
      { kind: "profile", label: "Profile 1" },
      { kind: "connection", label: "Connected" },
    ]);
  });

  test("device top bar keeps the connection first and profile second", () => {
    expect(
      buildHeaderChips("Device", {
        activeProfile: "Desk Setup",
        connectionLabel: "Connected",
        firmware: "BYT-0x010C-preview",
        syncState: "Live session",
      }),
    ).toEqual([
      { kind: "connection", label: "Connected" },
      { kind: "profile", label: "Desk Setup" },
    ]);
  });

  test("lighting hides the device card while dashboard keeps it", () => {
    expect(shouldShowDeviceCard("Lighting")).toBe(false);
    expect(shouldShowDeviceCard("Dashboard")).toBe(false);
    expect(shouldShowDeviceCard("Device")).toBe(true);
  });
});

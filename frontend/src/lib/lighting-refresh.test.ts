import { expect, test } from "bun:test";

import {
  LIGHTING_AUTO_REFRESH_INTERVAL_MS,
  LIGHTING_INTERACTION_COOLDOWN_MS,
  computeNextLightingRefreshDelay,
  shouldAutoRefreshLighting,
} from "./lighting-refresh";

test("lighting auto-refresh only runs when the screen is visible and clean", () => {
  expect(
    shouldAutoRefreshLighting({
      isLightingScreen: true,
      stagedEditCount: 0,
      isDocumentVisible: true,
    }),
  ).toBe(true);

  expect(
    shouldAutoRefreshLighting({
      isLightingScreen: false,
      stagedEditCount: 0,
      isDocumentVisible: true,
    }),
  ).toBe(false);

  expect(
    shouldAutoRefreshLighting({
      isLightingScreen: true,
      stagedEditCount: 2,
      isDocumentVisible: true,
    }),
  ).toBe(false);

  expect(
    shouldAutoRefreshLighting({
      isLightingScreen: true,
      stagedEditCount: 0,
      isDocumentVisible: false,
    }),
  ).toBe(false);
});

test("lighting refresh delay honors both poll cadence and interaction cooldown", () => {
  const now = 50_000;
  const lastRefreshAt = 45_000;
  const lastInteractionAt = 48_000;

  expect(
    computeNextLightingRefreshDelay({
      now,
      lastRefreshAt,
      lastInteractionAt,
    }),
  ).toBe(
    Math.max(
      LIGHTING_AUTO_REFRESH_INTERVAL_MS - (now - lastRefreshAt),
      LIGHTING_INTERACTION_COOLDOWN_MS - (now - lastInteractionAt),
      0,
    ),
  );
});

export const LIGHTING_AUTO_REFRESH_INTERVAL_MS = 10_000;
export const LIGHTING_INTERACTION_COOLDOWN_MS = 4_000;

export interface LightingRefreshState {
  isLightingScreen: boolean;
  stagedEditCount: number;
  isDocumentVisible: boolean;
}

export interface LightingRefreshTiming {
  now: number;
  lastRefreshAt: number;
  lastInteractionAt: number;
}

export function shouldAutoRefreshLighting(state: LightingRefreshState): boolean {
  return state.isLightingScreen && state.stagedEditCount === 0 && state.isDocumentVisible;
}

export function computeNextLightingRefreshDelay(timing: LightingRefreshTiming): number {
  const refreshDelay = LIGHTING_AUTO_REFRESH_INTERVAL_MS - (timing.now - timing.lastRefreshAt);
  const interactionDelay =
    LIGHTING_INTERACTION_COOLDOWN_MS - (timing.now - timing.lastInteractionAt);

  return Math.max(refreshDelay, interactionDelay, 0);
}

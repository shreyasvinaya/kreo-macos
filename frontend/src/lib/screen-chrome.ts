import type { PrimaryScreen } from "./navigation";

interface HeaderChipInput {
  activeProfile: string;
  connectionLabel: string;
  firmware: string;
  syncState: string;
}

export function shouldShowDeviceCard(screen: PrimaryScreen): boolean {
  return screen === "Device";
}

export function buildHeaderChips(
  screen: PrimaryScreen,
  input: HeaderChipInput,
): string[] {
  if (screen === "Lighting") {
    return [input.activeProfile, input.connectionLabel];
  }

  if (screen === "Device") {
    return [input.connectionLabel, input.activeProfile];
  }

  if (screen === "Events") {
    return [input.connectionLabel];
  }

  return [input.activeProfile, input.syncState, input.firmware];
}

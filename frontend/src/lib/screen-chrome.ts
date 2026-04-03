import type { PrimaryScreen } from "./navigation";

interface HeaderChipInput {
  activeProfile: string;
  connectionLabel: string;
  firmware: string;
  syncState: string;
}

export interface HeaderChip {
  kind: "profile" | "connection" | "text";
  label: string;
}

export function shouldShowDeviceCard(screen: PrimaryScreen): boolean {
  return screen === "Device";
}

export function buildHeaderChips(
  screen: PrimaryScreen,
  input: HeaderChipInput,
): HeaderChip[] {
  if (screen === "Lighting") {
    return [
      { kind: "profile", label: input.activeProfile },
      { kind: "connection", label: input.connectionLabel },
    ];
  }

  if (screen === "Device") {
    return [
      { kind: "connection", label: input.connectionLabel },
      { kind: "profile", label: input.activeProfile },
    ];
  }

  if (screen === "Events") {
    return [{ kind: "connection", label: input.connectionLabel }];
  }

  return [
    { kind: "profile", label: input.activeProfile },
    { kind: "text", label: input.syncState },
    { kind: "text", label: input.firmware },
  ];
}

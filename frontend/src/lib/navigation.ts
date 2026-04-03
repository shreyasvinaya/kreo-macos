export const primaryNavigation = [
  "Dashboard",
  "Device",
  "Keymap",
  "Lighting",
  "Macros",
  "Profiles",
  "Events",
  "Settings",
] as const;

export type PrimaryScreen = (typeof primaryNavigation)[number];

export const defaultScreen: PrimaryScreen = "Dashboard";

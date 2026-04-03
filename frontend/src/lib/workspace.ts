import type { PrimaryScreen } from "./navigation";

export interface WorkspaceContent {
  headerKicker: string;
  headerTitle: string;
  keyboardTitle: string;
  selectionLabel: string;
  inspectorTitle: string;
}

const workspaceContent: Record<PrimaryScreen, WorkspaceContent> = {
  Dashboard: {
    headerKicker: "Overview",
    headerTitle: "Dashboard",
    keyboardTitle: "Workspace",
    selectionLabel: "Overview",
    inspectorTitle: "Overview",
  },
  Device: {
    headerKicker: "Hardware",
    headerTitle: "Device",
    keyboardTitle: "Connection Details",
    selectionLabel: "Technical details",
    inspectorTitle: "Capabilities",
  },
  Keymap: {
    headerKicker: "Editor",
    headerTitle: "Keymap",
    keyboardTitle: "Base Layer",
    selectionLabel: "Editing: Right Option",
    inspectorTitle: "Key Assignment",
  },
  Lighting: {
    headerKicker: "Editor",
    headerTitle: "Lighting",
    keyboardTitle: "Lighting Preview",
    selectionLabel: "Preview: Right Option",
    inspectorTitle: "Lighting Details",
  },
  Macros: {
    headerKicker: "Editor",
    headerTitle: "Macros",
    keyboardTitle: "Macro Bindings",
    selectionLabel: "Binding: Right Option",
    inspectorTitle: "Macro Assignment",
  },
  Profiles: {
    headerKicker: "Configuration",
    headerTitle: "Profiles",
    keyboardTitle: "Profile Layout",
    selectionLabel: "Profile: Profile 1",
    inspectorTitle: "Profile Details",
  },
  Events: {
    headerKicker: "Diagnostics",
    headerTitle: "Events",
    keyboardTitle: "Recent Device Events",
    selectionLabel: "Activity log",
    inspectorTitle: "Event Details",
  },
  Settings: {
    headerKicker: "Configuration",
    headerTitle: "Settings",
    keyboardTitle: "Device Preferences",
    selectionLabel: "Device: Kreo Swarm",
    inspectorTitle: "Application Settings",
  },
};

export function buildWorkspaceContent(screen: PrimaryScreen): WorkspaceContent {
  return workspaceContent[screen];
}

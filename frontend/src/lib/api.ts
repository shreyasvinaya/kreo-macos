import type { ConnectionStatus } from "./status";
import { buildPerKeyApplyPayload, type PerKeyLightingEntry } from "./lighting";
import { normalizeKeyboardAsset, type KeyboardAssetModel, type KeyboardAssetResponse } from "./keyboard-assets";
import type {
  KeyActionModel,
  KeyAssignmentModel,
  KeymapEditPayload,
  KeymapModel,
} from "./keymap";

export type { KeyboardAssetModel } from "./keyboard-assets";
export type { KeymapEditPayload, KeymapModel } from "./keymap";

export interface DeviceSummary {
  activeProfile: string;
  connected: boolean;
  configurable: boolean;
  dirty: boolean;
  firmware: string;
  interfaceName: string;
  protocol: string;
  status: ConnectionStatus;
  supportedDevices: string[];
  supportsProfiles: boolean;
  syncState: string;
  targetName: string;
}

export interface TraceEntry {
  direction: "read" | "write" | "meta";
  label: string;
  payloadHex: string;
  reportId: number;
  timestamp: string;
}

export interface DashboardModel {
  device: DeviceSummary;
  profiles: {
    supported: boolean;
    activeProfile: number | null;
    availableProfiles: number[];
    reason: string | null;
    storageKind: string;
    activeSnapshotId: string | null;
    snapshots: SavedProfileModel[];
  };
  traceEntries: TraceEntry[];
}

export interface SavedKeymapAssignmentModel {
  baseRawValue: number;
  fnRawValue: number;
}

export interface SavedProfileModel {
  snapshotId: string;
  name: string;
  updatedAt: string;
  lighting: {
    mode: string;
    brightness: number;
    color: string | null;
    keys: Record<string, string>;
  };
  keymap: {
    assignments: Record<string, SavedKeymapAssignmentModel>;
  };
}

export interface SavedProfilesModel {
  supported: boolean;
  activeProfile: number | null;
  availableProfiles: number[];
  reason: string | null;
  storageKind: string;
  activeSnapshotId: string | null;
  snapshots: SavedProfileModel[];
}

export interface PerKeyLightingModel {
  mode: string;
  brightness: number;
  perKeyRgbSupported: boolean;
  verificationStatus: string;
  keys: PerKeyLightingEntry[];
}

export interface LightingResponseModel {
  mode: string;
  brightness: number;
  color: string | null;
  perKeyRgbSupported: boolean;
  verificationStatus: string;
}

export interface GlobalLightingApplyPayload {
  mode: string;
  brightness: number | null;
  color: string | null;
}

export interface MacroActionModel {
  key: string;
  eventType: string;
  delayMs: number;
}

export interface MacroSlotModel {
  slotId: number;
  name: string;
  executionType: string;
  cycleTimes: number;
  boundUiKeys: string[];
  actions: MacroActionModel[];
}

export interface MacrosModel {
  supported: boolean;
  reason: string | null;
  verificationStatus: string;
  nextSlotId: number;
  maxSlots: number;
  slots: MacroSlotModel[];
}

export interface MacroUpsertModel {
  name: string;
  boundUiKey: string | null;
  executionType: string;
  cycleTimes: number;
  actions: MacroActionModel[];
}

interface DeviceResponse {
  connected: boolean;
  configurable: boolean;
  supported_devices: string[];
  supports_profiles: boolean;
  transport_kind: string;
}

interface ProfilesResponse {
  supported: boolean;
  active_profile: number | null;
  available_profiles: number[];
  reason: string | null;
  storage_kind: string;
  active_snapshot_id: string | null;
  snapshots: SavedProfileResponse[];
}

interface SavedKeymapAssignmentResponse {
  base_raw_value: number;
  fn_raw_value: number;
}

interface SavedProfileResponse {
  snapshot_id: string;
  name: string;
  updated_at: string;
  lighting: {
    mode: string;
    brightness: number;
    color: string | null;
    keys: Record<string, string>;
  };
  keymap: {
    assignments: Record<string, SavedKeymapAssignmentResponse>;
  };
}

interface KeyActionResponse {
  action_id: string;
  label: string;
  category: string;
  raw_value: number;
}

interface KeyAssignmentResponse {
  ui_key: string;
  logical_id: string;
  svg_id: string;
  label: string;
  protocol_pos: number;
  base_action: KeyActionResponse;
  fn_action: KeyActionResponse;
}

interface KeymapResponse {
  verification_status: string;
  assignments: KeyAssignmentResponse[];
  available_actions: KeyActionResponse[];
}

interface PerKeyLightingEntryResponse {
  ui_key: string;
  label: string;
  light_pos: number;
  color: string;
}

interface PerKeyLightingResponse {
  mode: string;
  brightness: number;
  per_key_rgb_supported: boolean;
  verification_status: string;
  keys: PerKeyLightingEntryResponse[];
}

interface LightingApplyResponse {
  mode: string;
  brightness: number;
  per_key_rgb_supported: boolean;
  color: string | null;
  verification_status: string;
}

interface MacroActionResponse {
  key: string;
  event_type: string;
  delay_ms: number;
}

interface MacroSlotResponse {
  slot_id: number;
  name: string;
  execution_type: string;
  cycle_times: number;
  bound_ui_keys: string[];
  actions: MacroActionResponse[];
}

interface MacrosResponse {
  supported: boolean;
  reason: string | null;
  verification_status: string;
  next_slot_id: number;
  max_slots: number;
  slots: MacroSlotResponse[];
}

const fallbackDashboard: DashboardModel = {
  device: {
    activeProfile: "Profile 1",
    connected: false,
    configurable: false,
    dirty: false,
    firmware: "BYT-0x010C-preview",
    interfaceName: "No supported HID transport",
    protocol: "bytech",
    status: "disconnected",
    supportedDevices: ["Kreo Swarm"],
    supportsProfiles: false,
    syncState: "Waiting for keyboard",
    targetName: "Kreo Swarm",
  },
  profiles: {
    supported: true,
    activeProfile: null,
    availableProfiles: [],
    reason: null,
    storageKind: "saved_snapshots",
    activeSnapshotId: null,
    snapshots: [],
  },
  traceEntries: [
    {
      direction: "write",
      label: "Preview vendor probe",
      payloadHex: "05 01 00 00 00 00 00 00",
      reportId: 5,
      timestamp: "09:41:12",
    },
    {
      direction: "read",
      label: "Preview controller response",
      payloadHex: "06 10 0c 00 01 00 00 00",
      reportId: 6,
      timestamp: "09:41:12",
    },
    {
      direction: "meta",
      label: "Session note",
      payloadHex: "right option target staged for remap editor",
      reportId: 0,
      timestamp: "09:41:13",
    },
  ],
};

export async function loadDashboardModel(): Promise<DashboardModel> {
  try {
    const [deviceResponse, profilesResponse] = await Promise.all([
      fetch("/api/device"),
      fetch("/api/profiles"),
    ]);
    if (!deviceResponse.ok) {
      throw new Error(`device endpoint returned ${deviceResponse.status}`);
    }
    if (!profilesResponse.ok) {
      throw new Error(`profiles endpoint returned ${profilesResponse.status}`);
    }

    const payload = (await deviceResponse.json()) as DeviceResponse;
    const profiles = (await profilesResponse.json()) as ProfilesResponse;

    const interfaceName =
      payload.transport_kind === "vendor_hid"
        ? "usagePage 0xFF00 / usage 0x01"
        : payload.transport_kind === "wireless_receiver"
          ? "usagePage 0xFF02 / usage 0x02"
          : fallbackDashboard.device.interfaceName;
    const syncState =
      payload.transport_kind === "vendor_hid"
        ? "Vendor HID live"
        : payload.transport_kind === "wireless_receiver"
          ? "Wireless receiver live"
          : "Waiting for keyboard";
    const activeSnapshot = profiles.snapshots.find(
      (snapshot) => snapshot.snapshot_id === profiles.active_snapshot_id,
    );
    const activeProfile =
      activeSnapshot?.name ??
      (profiles.supported ? "No saved profile" : "Profiles unavailable");

    return {
      device: {
        activeProfile,
        connected: payload.connected,
        configurable: payload.configurable,
        dirty: false,
        firmware:
          payload.transport_kind === "wireless_receiver"
            ? "Detected live receiver"
            : payload.connected
              ? "Detected live device"
              : "BYT-0x010C-preview",
        interfaceName,
        protocol: "bytech",
        status: payload.connected ? "connected" : "disconnected",
        supportedDevices:
          payload.supported_devices.length > 0
            ? payload.supported_devices
            : fallbackDashboard.device.supportedDevices,
        supportsProfiles: payload.supports_profiles,
        syncState: payload.connected ? syncState : "Waiting for keyboard",
        targetName: payload.supported_devices[0] ?? fallbackDashboard.device.targetName,
      },
      profiles: {
        supported: profiles.supported,
        activeProfile: profiles.active_profile,
        availableProfiles: profiles.available_profiles,
        reason: profiles.reason,
        storageKind: profiles.storage_kind,
        activeSnapshotId: profiles.active_snapshot_id,
        snapshots: profiles.snapshots.map(normalizeSavedProfile),
      },
      traceEntries: fallbackDashboard.traceEntries,
    };
  } catch {
    return fallbackDashboard;
  }
}

function normalizeSavedProfile(payload: SavedProfileResponse): SavedProfileModel {
  return {
    snapshotId: payload.snapshot_id,
    name: payload.name,
    updatedAt: payload.updated_at,
    lighting: {
      mode: payload.lighting.mode,
      brightness: payload.lighting.brightness,
      color: payload.lighting.color,
      keys: payload.lighting.keys,
    },
    keymap: {
      assignments: Object.fromEntries(
        Object.entries(payload.keymap.assignments).map(([uiKey, assignment]) => [
          uiKey,
          {
            baseRawValue: assignment.base_raw_value,
            fnRawValue: assignment.fn_raw_value,
          },
        ]),
      ),
    },
  };
}

export async function loadSavedProfiles(): Promise<SavedProfilesModel> {
  const response = await fetch("/api/profiles");
  if (!response.ok) {
    throw new Error(`profiles endpoint returned ${response.status}`);
  }

  const payload = (await response.json()) as ProfilesResponse;
  return {
    supported: payload.supported,
    activeProfile: payload.active_profile,
    availableProfiles: payload.available_profiles,
    reason: payload.reason,
    storageKind: payload.storage_kind,
    activeSnapshotId: payload.active_snapshot_id,
    snapshots: payload.snapshots.map(normalizeSavedProfile),
  };
}

export async function createSavedProfile(name: string): Promise<SavedProfilesModel> {
  const response = await fetch("/api/profiles", {
    method: "POST",
    headers: {
      "content-type": "application/json",
    },
    body: JSON.stringify({ name }),
  });
  if (!response.ok) {
    throw new Error(`profile create endpoint returned ${response.status}`);
  }

  const payload = (await response.json()) as ProfilesResponse;
  return {
    supported: payload.supported,
    activeProfile: payload.active_profile,
    availableProfiles: payload.available_profiles,
    reason: payload.reason,
    storageKind: payload.storage_kind,
    activeSnapshotId: payload.active_snapshot_id,
    snapshots: payload.snapshots.map(normalizeSavedProfile),
  };
}

export async function applySavedProfile(snapshotId: string): Promise<SavedProfilesModel> {
  const response = await fetch(`/api/profiles/${snapshotId}/apply`, {
    method: "POST",
  });
  if (!response.ok) {
    throw new Error(`profile apply endpoint returned ${response.status}`);
  }

  const payload = (await response.json()) as ProfilesResponse;
  return {
    supported: payload.supported,
    activeProfile: payload.active_profile,
    availableProfiles: payload.available_profiles,
    reason: payload.reason,
    storageKind: payload.storage_kind,
    activeSnapshotId: payload.active_snapshot_id,
    snapshots: payload.snapshots.map(normalizeSavedProfile),
  };
}

function normalizePerKeyLighting(payload: PerKeyLightingResponse): PerKeyLightingModel {
  return {
    mode: payload.mode,
    brightness: payload.brightness,
    perKeyRgbSupported: payload.per_key_rgb_supported,
    verificationStatus: payload.verification_status,
    keys: payload.keys.map((entry) => ({
      uiKey: entry.ui_key,
      label: entry.label,
      lightPos: entry.light_pos,
      color: entry.color,
    })),
  };
}

export async function loadPerKeyLightingModel(): Promise<PerKeyLightingModel> {
  const response = await fetch("/api/lighting/per-key");
  if (!response.ok) {
    throw new Error(`per-key lighting endpoint returned ${response.status}`);
  }

  const payload = (await response.json()) as PerKeyLightingResponse;
  return normalizePerKeyLighting(payload);
}

export async function applyPerKeyLighting(
  stagedEdits: Record<string, string>,
): Promise<PerKeyLightingModel> {
  const response = await fetch("/api/lighting/per-key/apply", {
    method: "POST",
    headers: {
      "content-type": "application/json",
    },
    body: JSON.stringify(buildPerKeyApplyPayload(stagedEdits)),
  });
  if (!response.ok) {
    throw new Error(`per-key apply endpoint returned ${response.status}`);
  }

  const payload = (await response.json()) as PerKeyLightingResponse;
  return normalizePerKeyLighting(payload);
}

export async function applyGlobalLighting(
  payload: GlobalLightingApplyPayload,
): Promise<LightingResponseModel> {
  const response = await fetch("/api/lighting/apply", {
    method: "POST",
    headers: {
      "content-type": "application/json",
    },
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    throw new Error(`lighting apply endpoint returned ${response.status}`);
  }

  const result = (await response.json()) as LightingApplyResponse;
  return {
    mode: result.mode,
    brightness: result.brightness,
    color: result.color,
    perKeyRgbSupported: result.per_key_rgb_supported,
    verificationStatus: result.verification_status,
  };
}

export async function loadKeyboardAsset(assetName: string): Promise<KeyboardAssetModel> {
  const response = await fetch(`/api/keyboard-assets/${assetName}`);
  if (!response.ok) {
    throw new Error(`keyboard asset endpoint returned ${response.status}`);
  }

  const payload = (await response.json()) as KeyboardAssetResponse;
  return normalizeKeyboardAsset(payload);
}

function normalizeKeyAction(payload: KeyActionResponse): KeyActionModel {
  return {
    actionId: payload.action_id,
    label: payload.label,
    category: payload.category,
    rawValue: payload.raw_value,
  };
}

function normalizeKeyAssignment(payload: KeyAssignmentResponse): KeyAssignmentModel {
  return {
    uiKey: payload.ui_key,
    logicalId: payload.logical_id,
    svgId: payload.svg_id,
    label: payload.label,
    protocolPos: payload.protocol_pos,
    baseAction: normalizeKeyAction(payload.base_action),
    fnAction: normalizeKeyAction(payload.fn_action),
  };
}

export async function loadKeymapModel(): Promise<KeymapModel> {
  const response = await fetch("/api/keymap");
  if (!response.ok) {
    throw new Error(`keymap endpoint returned ${response.status}`);
  }

  const payload = (await response.json()) as KeymapResponse;
  return {
    verificationStatus: payload.verification_status,
    assignments: payload.assignments.map(normalizeKeyAssignment),
    availableActions: payload.available_actions.map(normalizeKeyAction),
  };
}

export async function applyKeymapEdits(
  edits: Record<string, KeymapEditPayload>,
): Promise<KeymapModel> {
  const response = await fetch("/api/keymap/apply", {
    method: "POST",
    headers: {
      "content-type": "application/json",
    },
    body: JSON.stringify({ edits }),
  });
  if (!response.ok) {
    throw new Error(`keymap apply endpoint returned ${response.status}`);
  }

  const payload = (await response.json()) as KeymapResponse;
  return {
    verificationStatus: payload.verification_status,
    assignments: payload.assignments.map(normalizeKeyAssignment),
    availableActions: payload.available_actions.map(normalizeKeyAction),
  };
}

function normalizeMacroAction(payload: MacroActionResponse): MacroActionModel {
  return {
    key: payload.key,
    eventType: payload.event_type,
    delayMs: payload.delay_ms,
  };
}

function normalizeMacroSlot(payload: MacroSlotResponse): MacroSlotModel {
  return {
    slotId: payload.slot_id,
    name: payload.name,
    executionType: payload.execution_type,
    cycleTimes: payload.cycle_times,
    boundUiKeys: payload.bound_ui_keys,
    actions: payload.actions.map(normalizeMacroAction),
  };
}

function normalizeMacrosModel(payload: MacrosResponse): MacrosModel {
  return {
    supported: payload.supported,
    reason: payload.reason,
    verificationStatus: payload.verification_status,
    nextSlotId: payload.next_slot_id,
    maxSlots: payload.max_slots,
    slots: payload.slots.map(normalizeMacroSlot),
  };
}

export async function loadMacrosModel(): Promise<MacrosModel> {
  const response = await fetch("/api/macros");
  if (!response.ok) {
    throw new Error(`macros endpoint returned ${response.status}`);
  }

  const payload = (await response.json()) as MacrosResponse;
  return normalizeMacrosModel(payload);
}

export async function upsertMacro(
  slotId: number,
  payload: MacroUpsertModel,
): Promise<MacrosModel> {
  const response = await fetch(`/api/macros/${slotId}`, {
    method: "PUT",
    headers: {
      "content-type": "application/json",
    },
    body: JSON.stringify({
      name: payload.name,
      bound_ui_key: payload.boundUiKey,
      execution_type: payload.executionType,
      cycle_times: payload.cycleTimes,
      actions: payload.actions.map((action) => ({
        key: action.key,
        event_type: action.eventType,
        delay_ms: action.delayMs,
      })),
    }),
  });
  if (!response.ok) {
    throw new Error(`macro upsert endpoint returned ${response.status}`);
  }

  const result = (await response.json()) as MacrosResponse;
  return normalizeMacrosModel(result);
}

export async function deleteMacro(slotId: number): Promise<MacrosModel> {
  const response = await fetch(`/api/macros/${slotId}`, {
    method: "DELETE",
  });
  if (!response.ok) {
    throw new Error(`macro delete endpoint returned ${response.status}`);
  }

  const result = (await response.json()) as MacrosResponse;
  return normalizeMacrosModel(result);
}

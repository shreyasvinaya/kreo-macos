import type { ConnectionStatus } from "./status";
import { buildPerKeyApplyPayload, type PerKeyLightingEntry } from "./lighting";

export interface DeviceSummary {
  activeProfile: string;
  connected: boolean;
  dirty: boolean;
  firmware: string;
  interfaceName: string;
  protocol: string;
  status: ConnectionStatus;
  supportedDevices: string[];
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
  traceEntries: TraceEntry[];
}

export interface PerKeyLightingModel {
  mode: string;
  brightness: number;
  perKeyRgbSupported: boolean;
  verificationStatus: string;
  keys: PerKeyLightingEntry[];
}

interface DeviceResponse {
  connected: boolean;
  supported_devices: string[];
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

const fallbackDashboard: DashboardModel = {
  device: {
    activeProfile: "Profile 1",
    connected: false,
    dirty: false,
    firmware: "BYT-0x010C-preview",
    interfaceName: "usagePage 0xFF00 / usage 0x01",
    protocol: "bytech",
    status: "disconnected",
    supportedDevices: ["Kreo Swarm"],
    syncState: "Waiting for keyboard",
    targetName: "Kreo Swarm",
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
    const response = await fetch("/api/device");
    if (!response.ok) {
      throw new Error(`device endpoint returned ${response.status}`);
    }

    const payload = (await response.json()) as DeviceResponse;

    return {
      device: {
        activeProfile: "Profile 1",
        connected: payload.connected,
        dirty: false,
        firmware: payload.connected ? "Detected live device" : "BYT-0x010C-preview",
        interfaceName: "usagePage 0xFF00 / usage 0x01",
        protocol: "bytech",
        status: payload.connected ? "connected" : "disconnected",
        supportedDevices:
          payload.supported_devices.length > 0
            ? payload.supported_devices
            : fallbackDashboard.device.supportedDevices,
        syncState: payload.connected ? "Live session" : "Waiting for keyboard",
        targetName: payload.supported_devices[0] ?? fallbackDashboard.device.targetName,
      },
      traceEntries: fallbackDashboard.traceEntries,
    };
  } catch {
    return fallbackDashboard;
  }
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

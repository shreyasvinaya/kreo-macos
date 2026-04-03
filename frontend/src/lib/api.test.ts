import { afterEach, describe, expect, mock, test } from "bun:test";

import {
  applyKeymapEdits,
  applyGlobalLighting,
  deleteMacro,
  loadDashboardModel,
  loadKeyboardAsset,
  loadKeymapModel,
  loadMacrosModel,
  loadSavedProfiles,
  upsertMacro,
} from "./api";

const originalFetch = globalThis.fetch;

afterEach(() => {
  globalThis.fetch = originalFetch;
});

describe("loadDashboardModel", () => {
  test("normalizes a wireless receiver session and empty saved snapshot storage", async () => {
    globalThis.fetch = mock(async (input: string | URL | Request) => {
      const url = typeof input === "string" ? input : input.toString();

      if (url === "/api/device") {
        return new Response(
          JSON.stringify({
            connected: true,
            configurable: true,
            supported_devices: ["Kreo Swarm"],
            supports_profiles: false,
            transport_kind: "wireless_receiver",
          }),
          { status: 200 },
        );
      }

      if (url === "/api/profiles") {
        return new Response(
          JSON.stringify({
            supported: true,
            active_profile: null,
            available_profiles: [],
            reason: null,
            storage_kind: "saved_snapshots",
            active_snapshot_id: null,
            snapshots: [],
          }),
          { status: 200 },
        );
      }

      throw new Error(`unexpected fetch: ${url}`);
    }) as unknown as typeof fetch;

    const model = await loadDashboardModel();

    expect(model.device.connected).toBe(true);
    expect(model.device.status).toBe("connected");
    expect(model.device.activeProfile).toBe("No saved profile");
    expect(model.device.interfaceName).toBe("usagePage 0xFF02 / usage 0x02");
    expect(model.device.syncState).toBe("Wireless receiver live");
    expect(model.profiles.supported).toBe(true);
    expect(model.profiles.storageKind).toBe("saved_snapshots");
  });

  test("normalizes a wired vendor HID session and active saved profile label", async () => {
    globalThis.fetch = mock(async (input: string | URL | Request) => {
      const url = typeof input === "string" ? input : input.toString();

      if (url === "/api/device") {
        return new Response(
          JSON.stringify({
            connected: true,
            configurable: true,
            supported_devices: ["Kreo Swarm"],
            supports_profiles: true,
            transport_kind: "vendor_hid",
          }),
          { status: 200 },
        );
      }

      if (url === "/api/profiles") {
        return new Response(
          JSON.stringify({
            supported: true,
            active_profile: 1,
            available_profiles: [1],
            reason: null,
            storage_kind: "saved_snapshots",
            active_snapshot_id: "desk-setup",
            snapshots: [
              {
                snapshot_id: "desk-setup",
                name: "Desk Setup",
                updated_at: "2026-04-03T00:00:00Z",
                lighting: {
                  mode: "custom",
                  brightness: 25,
                  color: null,
                  keys: {
                    esc: "#ff0000",
                  },
                },
                keymap: {
                  assignments: {
                    esc: {
                      base_raw_value: 10496,
                      fn_raw_value: 33554658,
                    },
                  },
                },
                macros: {
                  supported: true,
                  reason: null,
                  slots: [
                    {
                      slot_id: 0,
                      name: "Copy Burst",
                      execution_type: "FIXED_COUNT",
                      cycle_times: 2,
                      bound_ui_keys: ["right_opt"],
                      actions: [
                        { key: "c", event_type: "press", delay_ms: 10 },
                        { key: "c", event_type: "release", delay_ms: 20 },
                      ],
                    },
                  ],
                },
              },
            ],
          }),
          { status: 200 },
        );
      }

      throw new Error(`unexpected fetch: ${url}`);
    }) as unknown as typeof fetch;

    const model = await loadDashboardModel();

    expect(model.device.activeProfile).toBe("Desk Setup");
    expect(model.device.interfaceName).toBe("usagePage 0xFF00 / usage 0x01");
    expect(model.device.syncState).toBe("Vendor HID live");
    expect(model.profiles.activeProfile).toBe(1);
    expect(model.profiles.activeSnapshotId).toBe("desk-setup");
  });
});

describe("loadSavedProfiles", () => {
  test("normalizes saved snapshot payloads", async () => {
    globalThis.fetch = mock(async (input: string | URL | Request) => {
      const url = typeof input === "string" ? input : input.toString();

      if (url === "/api/profiles") {
        return new Response(
          JSON.stringify({
            supported: true,
            active_profile: 1,
            available_profiles: [1],
            reason: null,
            storage_kind: "saved_snapshots",
            active_snapshot_id: "desk-setup",
            snapshots: [
              {
                snapshot_id: "desk-setup",
                name: "Desk Setup",
                updated_at: "2026-04-03T00:00:00Z",
                lighting: {
                  mode: "custom",
                  brightness: 25,
                  color: null,
                  keys: {
                    esc: "#ff0000",
                    w: "#00ffaa",
                  },
                },
                keymap: {
                  assignments: {
                    esc: {
                      base_raw_value: 10496,
                      fn_raw_value: 33554658,
                    },
                  },
                },
                macros: {
                  supported: true,
                  reason: null,
                  slots: [
                    {
                      slot_id: 0,
                      name: "Copy Burst",
                      execution_type: "FIXED_COUNT",
                      cycle_times: 2,
                      bound_ui_keys: ["right_opt"],
                      actions: [
                        { key: "c", event_type: "press", delay_ms: 10 },
                        { key: "c", event_type: "release", delay_ms: 20 },
                      ],
                    },
                  ],
                },
              },
            ],
          }),
          { status: 200 },
        );
      }

      throw new Error(`unexpected fetch: ${url}`);
    }) as unknown as typeof fetch;

    const profiles = await loadSavedProfiles();

    expect(profiles.storageKind).toBe("saved_snapshots");
    expect(profiles.activeSnapshotId).toBe("desk-setup");
    expect(profiles.snapshots[0]?.lighting.keys.esc).toBe("#ff0000");
    expect(profiles.snapshots[0]?.keymap.assignments.esc?.fnRawValue).toBe(33554658);
    expect(profiles.snapshots[0]?.macros.slots[0]?.name).toBe("Copy Burst");
  });
});

describe("loadKeyboardAsset", () => {
  test("fetches the swarm75 asset payload", async () => {
    globalThis.fetch = mock(async (input: string | URL | Request) => {
      const url = typeof input === "string" ? input : input.toString();

      if (url === "/api/keyboard-assets/swarm75") {
        return new Response(
          JSON.stringify({
            asset_name: "swarm75",
            base_image_url: "/keyboard/swarm75/base/default.webp",
            letters_image_url: "/keyboard/swarm75/letters/default.webp",
            interactive_svg_url: "/keyboard/swarm75/overlay/interactive.svg",
            keys: [],
          }),
          { status: 200 },
        );
      }

      throw new Error(`unexpected fetch: ${url}`);
    }) as unknown as typeof fetch;

    const asset = await loadKeyboardAsset("swarm75");

    expect(asset.assetName).toBe("swarm75");
    expect(asset.baseImageUrl).toBe("/keyboard/swarm75/base/default.webp");
  });
});

describe("loadKeymapModel", () => {
  test("normalizes typed key assignments and action catalog", async () => {
    globalThis.fetch = mock(async (input: string | URL | Request) => {
      const url = typeof input === "string" ? input : input.toString();

      if (url === "/api/keymap") {
        return new Response(
          JSON.stringify({
            verification_status: "verified",
            available_actions: [
              {
                action_id: "disabled",
                label: "Disabled",
                category: "System",
                raw_value: 0,
              },
            ],
            assignments: [
              {
                ui_key: "right_opt",
                logical_id: "RALT",
                svg_id: "key_RALT",
                label: "Command",
                protocol_pos: 220,
                base_action: {
                  action_id: "basic:right_opt",
                  label: "Command",
                  category: "Modifiers",
                  raw_value: 4194304,
                },
                fn_action: {
                  action_id: "disabled",
                  label: "Disabled",
                  category: "System",
                  raw_value: 0,
                },
              },
            ],
          }),
          { status: 200 },
        );
      }

      throw new Error(`unexpected fetch: ${url}`);
    }) as unknown as typeof fetch;

    const model = await loadKeymapModel();

    expect(model.verificationStatus).toBe("verified");
    expect(model.assignments[0]?.uiKey).toBe("right_opt");
    expect(model.assignments[0]?.baseAction.rawValue).toBe(4194304);
    expect(model.availableActions[0]?.actionId).toBe("disabled");
  });
});

describe("applyKeymapEdits", () => {
  test("surfaces backend detail text for protocol errors", async () => {
    globalThis.fetch = mock(async (input: string | URL | Request) => {
      const url = typeof input === "string" ? input : input.toString();

      if (url === "/api/keymap/apply") {
        return new Response(
          JSON.stringify({
            detail: "FN-layer remapping is not verified on this keyboard yet",
          }),
          { status: 422 },
        );
      }

      throw new Error(`unexpected fetch: ${url}`);
    }) as unknown as typeof fetch;

    await expect(
      applyKeymapEdits({
        right_opt: {
          fn_raw_value: 33554637,
        },
      }),
    ).rejects.toThrow("FN-layer remapping is not verified on this keyboard yet");
  });
});

describe("applyGlobalLighting", () => {
  test("posts preset lighting mode updates", async () => {
    globalThis.fetch = mock(async (input: string | URL | Request, init?: RequestInit) => {
      const url = typeof input === "string" ? input : input.toString();

      if (url === "/api/lighting/apply") {
        expect(init?.method).toBe("POST");
        expect(init?.body).toBe(
          JSON.stringify({
            mode: "wave",
            brightness: 50,
            color: null,
          }),
        );
        return new Response(
          JSON.stringify({
            mode: "wave",
            brightness: 50,
            per_key_rgb_supported: false,
            color: null,
            verification_status: "verified",
          }),
          { status: 200 },
        );
      }

      throw new Error(`unexpected fetch: ${url}`);
    }) as unknown as typeof fetch;

    const result = await applyGlobalLighting({
      mode: "wave",
      brightness: 50,
      color: null,
    });

    expect(result.mode).toBe("wave");
    expect(result.brightness).toBe(50);
    expect(result.verificationStatus).toBe("verified");
  });
});

describe("macros api", () => {
  test("normalizes wired macro payloads", async () => {
    globalThis.fetch = mock(async (input: string | URL | Request) => {
      const url = typeof input === "string" ? input : input.toString();

      if (url === "/api/macros") {
        return new Response(
          JSON.stringify({
            supported: true,
            reason: null,
            verification_status: "verified",
            next_slot_id: 1,
            max_slots: 16,
            slots: [
              {
                slot_id: 0,
                name: "Copy Burst",
                execution_type: "FIXED_COUNT",
                cycle_times: 3,
                bound_ui_keys: ["right_opt"],
                actions: [
                  { key: "c", event_type: "press", delay_ms: 12 },
                  { key: "c", event_type: "release", delay_ms: 24 },
                ],
              },
            ],
          }),
          { status: 200 },
        );
      }

      throw new Error(`unexpected fetch: ${url}`);
    }) as unknown as typeof fetch;

    const model = await loadMacrosModel();

    expect(model.supported).toBe(true);
    expect(model.nextSlotId).toBe(1);
    expect(model.slots[0]?.boundUiKeys).toEqual(["right_opt"]);
    expect(model.slots[0]?.actions[0]?.eventType).toBe("press");
  });

  test("upserts a macro slot", async () => {
    globalThis.fetch = mock(async (input: string | URL | Request, init?: RequestInit) => {
      const url = typeof input === "string" ? input : input.toString();

      if (url === "/api/macros/0") {
        expect(init?.method).toBe("PUT");
        expect(init?.body).toBe(
          JSON.stringify({
            name: "Launch Focus",
            bound_ui_key: "right_opt",
            execution_type: "UNTIL_ANY_PRESSED",
            cycle_times: 1,
            actions: [
              { key: "q", event_type: "press", delay_ms: 10 },
              { key: "q", event_type: "release", delay_ms: 20 },
            ],
          }),
        );
        return new Response(
          JSON.stringify({
            supported: true,
            reason: null,
            verification_status: "verified",
            next_slot_id: 1,
            max_slots: 16,
            slots: [
              {
                slot_id: 0,
                name: "Launch Focus",
                execution_type: "UNTIL_ANY_PRESSED",
                cycle_times: 1,
                bound_ui_keys: ["right_opt"],
                actions: [
                  { key: "q", event_type: "press", delay_ms: 10 },
                  { key: "q", event_type: "release", delay_ms: 20 },
                ],
              },
            ],
          }),
          { status: 200 },
        );
      }

      throw new Error(`unexpected fetch: ${url}`);
    }) as unknown as typeof fetch;

    const model = await upsertMacro(0, {
      name: "Launch Focus",
      boundUiKey: "right_opt",
      executionType: "UNTIL_ANY_PRESSED",
      cycleTimes: 1,
      actions: [
        { key: "q", eventType: "press", delayMs: 10 },
        { key: "q", eventType: "release", delayMs: 20 },
      ],
    });

    expect(model.slots[0]?.name).toBe("Launch Focus");
    expect(model.slots[0]?.executionType).toBe("UNTIL_ANY_PRESSED");
  });

  test("deletes a macro slot", async () => {
    globalThis.fetch = mock(async (input: string | URL | Request, init?: RequestInit) => {
      const url = typeof input === "string" ? input : input.toString();

      if (url === "/api/macros/0") {
        expect(init?.method).toBe("DELETE");
        return new Response(
          JSON.stringify({
            supported: true,
            reason: null,
            verification_status: "verified",
            next_slot_id: 0,
            max_slots: 16,
            slots: [],
          }),
          { status: 200 },
        );
      }

      throw new Error(`unexpected fetch: ${url}`);
    }) as unknown as typeof fetch;

    const model = await deleteMacro(0);

    expect(model.slots).toEqual([]);
    expect(model.nextSlotId).toBe(0);
  });
});

import { describe, expect, test } from "bun:test";

import { buildKeymapColorsBySvgId } from "./keymap";

describe("buildKeymapColorsBySvgId", () => {
  test("keeps persisted remaps highlighted after staged edits are cleared", () => {
    const colors = buildKeymapColorsBySvgId(
      [
        {
          uiKey: "right_ctrl",
          logicalId: "RCTRL",
          svgId: "key_RCTRL",
          label: "Control",
          protocolPos: 268,
          baseAction: {
            actionId: "basic:right_opt",
            label: "Option Right",
            category: "Modifiers",
            rawValue: 0x00400000,
          },
          fnAction: {
            actionId: "disabled",
            label: "Disabled",
            category: "System",
            rawValue: 0,
          },
        },
        {
          uiKey: "right_opt",
          logicalId: "RALT",
          svgId: "key_RALT",
          label: "Command",
          protocolPos: 220,
          baseAction: {
            actionId: "basic:right_opt",
            label: "Option Right",
            category: "Modifiers",
            rawValue: 0x00400000,
          },
          fnAction: {
            actionId: "disabled",
            label: "Disabled",
            category: "System",
            rawValue: 0,
          },
        },
      ],
      {},
    );

    expect(colors.get("key_RCTRL")).toBe("#2d6a5f");
    expect(colors.get("key_RALT")).toBe("#273240");
  });

  test("uses the stronger staged tint while a remap edit is pending", () => {
    const colors = buildKeymapColorsBySvgId(
      [
        {
          uiKey: "right_ctrl",
          logicalId: "RCTRL",
          svgId: "key_RCTRL",
          label: "Control",
          protocolPos: 268,
          baseAction: {
            actionId: "basic:right_ctrl",
            label: "Control Right",
            category: "Modifiers",
            rawValue: 0x00100000,
          },
          fnAction: {
            actionId: "disabled",
            label: "Disabled",
            category: "System",
            rawValue: 0,
          },
        },
      ],
      {
        right_ctrl: {
          base_raw_value: 0x00400000,
        },
      },
    );

    expect(colors.get("key_RCTRL")).toBe("#355c7d");
  });
});

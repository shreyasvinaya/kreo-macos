import { expect, test } from "bun:test";

import { buildKeyboardLegendOverrides } from "./keyboard-assets";

test("keyboard legend overrides expose macOS modifier labels for the image surface", () => {
  expect(buildKeyboardLegendOverrides()).toEqual([
    { uiKey: "left_ctrl", label: "Control" },
    { uiKey: "left_cmd", label: "Option" },
    { uiKey: "left_opt", label: "Command" },
    { uiKey: "right_opt", label: "Command" },
    { uiKey: "right_ctrl", label: "Control" },
  ]);
});

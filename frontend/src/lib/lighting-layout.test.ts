import { expect, test } from "bun:test";

import {
  applyCheckerPattern,
  applySolidFill,
  applyThreeColorSplit,
  applyTwoColorSplit,
  buildEditableVisualOrder,
  flattenPhysicalKeyboardLayout,
  physicalKeyboardBlocks,
  physicalKeyboardLayout,
} from "./lighting-layout";

const keys = [
  { uiKey: "esc", label: "Esc", lightPos: 8, color: "#111111" },
  { uiKey: "f6", label: "F6", lightPos: 50, color: "#222222" },
  { uiKey: "right", label: "Right", lightPos: 103, color: "#333333" },
];

test("buildEditableVisualOrder follows the rendered board order", () => {
  expect(buildEditableVisualOrder(physicalKeyboardLayout, keys)).toEqual(["esc", "f6", "right"]);
});

test("physical keyboard is split into main utility and arrows blocks", () => {
  expect(physicalKeyboardBlocks.map((block) => block.id)).toEqual([
    "main",
    "utility",
    "arrows",
  ]);
});

test("bottom row uses macOS labels and keeps modifier keys editable", () => {
  const items = flattenPhysicalKeyboardLayout();

  expect(items.find((item) => item.id === "left_ctrl")?.label).toBe("Control");
  expect(items.find((item) => item.id === "left_cmd")?.label).toBe("Option");
  expect(items.find((item) => item.id === "left_opt")?.label).toBe("Command");
  expect(items.find((item) => item.id === "right_opt")?.label).toBe("Command");
  expect(items.find((item) => item.id === "right_ctrl")?.label).toBe("Control");
  expect(items.find((item) => item.id === "right_shift")?.editable).toBe(true);
  expect(items.find((item) => item.id === "fn")?.editable).toBe(true);
});

test("solid fill stages every mapped key", () => {
  expect(applySolidFill(keys, "#00ffaa")).toEqual({
    esc: "#00ffaa",
    f6: "#00ffaa",
    right: "#00ffaa",
  });
});

test("two-color split assigns left and right board groups deterministically", () => {
  expect(applyTwoColorSplit(keys, "#ff0000", "#0000ff")).toEqual({
    esc: "#ff0000",
    f6: "#0000ff",
    right: "#0000ff",
  });
});

test("three-color split assigns left center right groups deterministically", () => {
  expect(applyThreeColorSplit(keys, "#ff0000", "#00ff00", "#0000ff")).toEqual({
    esc: "#ff0000",
    f6: "#00ff00",
    right: "#0000ff",
  });
});

test("checker pattern alternates by rendered visual order", () => {
  expect(applyCheckerPattern(keys, "#ff0000", "#0000ff")).toEqual({
    esc: "#ff0000",
    f6: "#0000ff",
    right: "#ff0000",
  });
});

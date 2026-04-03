import type { PerKeyLightingEntry } from "./lighting";

export type PhysicalItemKind = "key" | "spacer" | "knob";
export type PhysicalKeySection = "function" | "main" | "utility" | "arrows" | "bottom";
export type PhysicalKeyWidth =
  | "standard"
  | "wide"
  | "wider"
  | "space"
  | "gap"
  | "cluster-gap"
  | "knob";

export interface PhysicalBoardItem {
  id: string;
  label: string;
  kind: PhysicalItemKind;
  section: PhysicalKeySection;
  width: PhysicalKeyWidth;
  editable: boolean;
}

export interface PhysicalKeyboardBlock {
  id: "main" | "utility" | "arrows";
  rows: PhysicalBoardItem[][];
}

function key(
  id: string,
  label: string,
  section: PhysicalKeySection,
  width: PhysicalKeyWidth = "standard",
  editable = true,
): PhysicalBoardItem {
  return {
    id,
    label,
    kind: "key",
    section,
    width,
    editable,
  };
}

function spacer(id: string, width: PhysicalKeyWidth = "gap"): PhysicalBoardItem {
  return {
    id,
    label: "",
    kind: "spacer",
    section: "main",
    width,
    editable: false,
  };
}

function knob(id: string): PhysicalBoardItem {
  return {
    id,
    label: "knob",
    kind: "knob",
    section: "utility",
    width: "knob",
    editable: false,
  };
}

export const physicalKeyboardBlocks: PhysicalKeyboardBlock[] = [
  {
    id: "main",
    rows: [
      [
        key("esc", "Esc", "function"),
        spacer("fn-gap-0", "cluster-gap"),
        key("f1", "F1", "function"),
        key("f2", "F2", "function"),
        key("f3", "F3", "function"),
        key("f4", "F4", "function"),
        spacer("fn-gap-1", "cluster-gap"),
        key("f5", "F5", "function"),
        key("f6", "F6", "function"),
        key("f7", "F7", "function"),
        key("f8", "F8", "function"),
        spacer("fn-gap-2", "cluster-gap"),
        key("f9", "F9", "function"),
        key("f10", "F10", "function"),
        key("f11", "F11", "function"),
        key("f12", "F12", "function"),
      ],
      [
        key("`", "`", "main"),
        key("1", "1", "main"),
        key("2", "2", "main"),
        key("3", "3", "main"),
        key("4", "4", "main"),
        key("5", "5", "main"),
        key("6", "6", "main"),
        key("7", "7", "main"),
        key("8", "8", "main"),
        key("9", "9", "main"),
        key("0", "0", "main"),
        key("-", "-", "main"),
        key("=", "=", "main"),
        key("backspace", "Backspace", "main", "wider"),
      ],
      [
        key("tab", "Tab", "main", "wide"),
        key("q", "Q", "main"),
        key("w", "W", "main"),
        key("e", "E", "main"),
        key("r", "R", "main"),
        key("t", "T", "main"),
        key("y", "Y", "main"),
        key("u", "U", "main"),
        key("i", "I", "main"),
        key("o", "O", "main"),
        key("p", "P", "main"),
        key("[", "[", "main"),
        key("]", "]", "main"),
        key("\\", "\\", "main"),
      ],
      [
        key("caps", "Caps", "main", "wide"),
        key("a", "A", "main"),
        key("s", "S", "main"),
        key("d", "D", "main"),
        key("f", "F", "main"),
        key("g", "G", "main"),
        key("h", "H", "main"),
        key("j", "J", "main"),
        key("k", "K", "main"),
        key("l", "L", "main"),
        key(";", ";", "main"),
        key("'", "'", "main"),
        key("enter", "Enter", "main", "wider"),
      ],
      [
        key("left_shift", "Shift", "main", "wide"),
        key("z", "Z", "main"),
        key("x", "X", "main"),
        key("c", "C", "main"),
        key("v", "V", "main"),
        key("b", "B", "main"),
        key("n", "N", "main"),
        key("m", "M", "main"),
        key(",", ",", "main"),
        key(".", ".", "main"),
        key("/", "/", "main"),
        key("right_shift", "Shift", "main", "wider"),
      ],
      [
        key("left_ctrl", "Control", "bottom"),
        key("left_cmd", "Option", "bottom"),
        key("left_opt", "Command", "bottom"),
        key("space", "Space", "bottom", "space"),
        key("right_opt", "Command", "bottom"),
        key("fn", "Fn", "bottom"),
        key("right_ctrl", "Control", "bottom"),
      ],
    ],
  },
  {
    id: "utility",
    rows: [
      [key("print_screen", "PrtSc", "utility"), knob("volume_knob")],
      [key("delete", "Del", "utility")],
      [key("page_up", "PgUp", "utility")],
      [key("page_down", "PgDn", "utility")],
      [key("end", "End", "utility")],
    ],
  },
  {
    id: "arrows",
    rows: [
      [spacer("arrow-gap-top", "cluster-gap"), key("up", "Up", "arrows")],
      [key("left", "Left", "arrows"), key("down", "Down", "arrows"), key("right", "Right", "arrows")],
    ],
  },
];

export function flattenPhysicalKeyboardLayout(): PhysicalBoardItem[] {
  return physicalKeyboardBlocks.flatMap((block) => block.rows.flat());
}

export const physicalKeyboardLayout = flattenPhysicalKeyboardLayout();

export function buildEditableVisualOrder(
  layout: PhysicalBoardItem[],
  keys: Pick<PerKeyLightingEntry, "uiKey">[],
): string[] {
  const availableKeys = new Set(keys.map((keyEntry) => keyEntry.uiKey));

  return layout
    .filter((item) => item.kind === "key" && item.editable && availableKeys.has(item.id))
    .map((item) => item.id);
}

function normalizeColor(color: string): string {
  return color.trim().toLowerCase();
}

function editsFromOrder(
  orderedKeys: string[],
  colorResolver: (index: number, length: number) => string,
): Record<string, string> {
  return Object.fromEntries(
    orderedKeys.map((uiKey, index) => [uiKey, normalizeColor(colorResolver(index, orderedKeys.length))]),
  );
}

export function applySolidFill(
  keys: PerKeyLightingEntry[],
  color: string,
): Record<string, string> {
  return editsFromOrder(buildEditableVisualOrder(physicalKeyboardLayout, keys), () => color);
}

export function applyTwoColorSplit(
  keys: PerKeyLightingEntry[],
  leftColor: string,
  rightColor: string,
): Record<string, string> {
  return editsFromOrder(
    buildEditableVisualOrder(physicalKeyboardLayout, keys),
    (index, length) => (index < Math.max(1, Math.floor(length / 2)) ? leftColor : rightColor),
  );
}

export function applyThreeColorSplit(
  keys: PerKeyLightingEntry[],
  leftColor: string,
  centerColor: string,
  rightColor: string,
): Record<string, string> {
  return editsFromOrder(
    buildEditableVisualOrder(physicalKeyboardLayout, keys),
    (index, length) => {
      const ratio = length <= 1 ? 0 : index / (length - 1);
      if (ratio < 1 / 3) {
        return leftColor;
      }
      if (ratio < 2 / 3) {
        return centerColor;
      }
      return rightColor;
    },
  );
}

export function applyCheckerPattern(
  keys: PerKeyLightingEntry[],
  primaryColor: string,
  secondaryColor: string,
): Record<string, string> {
  return editsFromOrder(
    buildEditableVisualOrder(physicalKeyboardLayout, keys),
    (index) => (index % 2 === 0 ? primaryColor : secondaryColor),
  );
}

function hueToHex(hue: number): string {
  const saturation = 1;
  const lightness = 0.5;
  const chroma = (1 - Math.abs(2 * lightness - 1)) * saturation;
  const secondary = chroma * (1 - Math.abs(((hue / 60) % 2) - 1));
  const match = lightness - chroma / 2;

  let red = 0;
  let green = 0;
  let blue = 0;

  if (hue < 60) {
    red = chroma;
    green = secondary;
  } else if (hue < 120) {
    red = secondary;
    green = chroma;
  } else if (hue < 180) {
    green = chroma;
    blue = secondary;
  } else if (hue < 240) {
    green = secondary;
    blue = chroma;
  } else if (hue < 300) {
    red = secondary;
    blue = chroma;
  } else {
    red = chroma;
    blue = secondary;
  }

  const toChannel = (value: number) =>
    Math.round((value + match) * 255)
      .toString(16)
      .padStart(2, "0");

  return `#${toChannel(red)}${toChannel(green)}${toChannel(blue)}`;
}

export function applyRainbowPreset(keys: PerKeyLightingEntry[]): Record<string, string> {
  return editsFromOrder(
    buildEditableVisualOrder(physicalKeyboardLayout, keys),
    (index, length) => hueToHex((index / Math.max(length, 1)) * 300),
  );
}

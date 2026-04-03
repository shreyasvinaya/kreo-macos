import { expect, test } from "bun:test";

import { applyLightingColorsToSvg, normalizeKeyboardAsset } from "./keyboard-assets";

test("normalizeKeyboardAsset maps backend keys by svg id and ui key", () => {
  const asset = normalizeKeyboardAsset({
    asset_name: "swarm75",
    base_image_url: "/keyboard/swarm75/base/default.webp",
    letters_image_url: "/keyboard/swarm75/letters/default.webp",
    interactive_svg_url: "/keyboard/swarm75/overlay/interactive.svg",
    keys: [
      {
        logical_id: "ESC",
        svg_id: "key_ESC",
        ui_key: "esc",
        label: "Esc",
        protocol_pos: 8,
        led_index: 0,
      },
    ],
  });

  expect(asset.keysBySvgId.get("key_ESC")?.uiKey).toBe("esc");
  expect(asset.keysByUiKey.get("esc")?.label).toBe("Esc");
});

test("applyLightingColorsToSvg fills known keys and dims unknown ones", () => {
  const svg = `
    <svg xmlns="http://www.w3.org/2000/svg">
      <path id="key_ESC" />
      <path id="key_FN" />
    </svg>
  `;

  const colored = applyLightingColorsToSvg(
    svg,
    new Map([
      ["key_ESC", "#00ffaa"],
      ["key_FN", "#273240"],
    ]),
    "key_ESC",
  );

  expect(colored).toContain('id="key_ESC"');
  expect(colored).toContain('fill="#00ffaa"');
  expect(colored).toContain('stroke="#ffffff"');
  expect(colored).toContain('id="key_FN"');
  expect(colored).toContain('fill="#273240"');
});

import { expect, test } from "bun:test";

import { buildPerKeyApplyPayload, buildRenderedLightingState } from "./lighting";

test("staged edits override device colors in rendered state", () => {
  const rendered = buildRenderedLightingState(
    [
      { uiKey: "esc", label: "Esc", lightPos: 8, color: "#ff0000" },
      { uiKey: "space", label: "Space", lightPos: 43, color: "#ffffff" },
    ],
    { esc: "#00ff00" },
  );

  expect(rendered.find((entry) => entry.uiKey === "esc")?.color).toBe("#00ff00");
  expect(rendered.find((entry) => entry.uiKey === "space")?.color).toBe("#ffffff");
});

test("apply payload only includes staged edits", () => {
  expect(buildPerKeyApplyPayload({ esc: "#00ff00" })).toEqual({
    edits: { esc: "#00ff00" },
  });
});

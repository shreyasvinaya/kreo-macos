export interface KeyboardAssetKeyResponse {
  logical_id: string;
  svg_id: string;
  ui_key: string;
  label: string;
  protocol_pos: number;
  led_index: number;
}

export interface KeyboardAssetResponse {
  asset_name: string;
  base_image_url: string;
  letters_image_url: string;
  interactive_svg_url: string;
  keys: KeyboardAssetKeyResponse[];
}

export interface KeyboardAssetKey {
  logicalId: string;
  svgId: string;
  uiKey: string;
  label: string;
  protocolPos: number;
  ledIndex: number;
}

export interface KeyboardAssetModel {
  assetName: string;
  baseImageUrl: string;
  lettersImageUrl: string;
  interactiveSvgUrl: string;
  keys: KeyboardAssetKey[];
  keysBySvgId: Map<string, KeyboardAssetKey>;
  keysByUiKey: Map<string, KeyboardAssetKey>;
}

export function normalizeKeyboardAsset(payload: KeyboardAssetResponse): KeyboardAssetModel {
  const keys = payload.keys.map((entry) => ({
    logicalId: entry.logical_id,
    svgId: entry.svg_id,
    uiKey: entry.ui_key,
    label: entry.label,
    protocolPos: entry.protocol_pos,
    ledIndex: entry.led_index,
  }));

  return {
    assetName: payload.asset_name,
    baseImageUrl: payload.base_image_url,
    lettersImageUrl: payload.letters_image_url,
    interactiveSvgUrl: payload.interactive_svg_url,
    keys,
    keysBySvgId: new Map(keys.map((entry) => [entry.svgId, entry])),
    keysByUiKey: new Map(keys.map((entry) => [entry.uiKey, entry])),
  };
}

export function applyLightingColorsToSvg(
  svgMarkup: string,
  colorsBySvgId: Map<string, string>,
  selectedSvgId: string | null,
): string {
  let result = svgMarkup;

  for (const [svgId, color] of colorsBySvgId) {
    const escapedId = svgId.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
    const selectedAttributes =
      selectedSvgId === svgId
        ? ' stroke="#ffffff" stroke-width="18" stroke-linejoin="round"'
        : ' stroke="#16202a" stroke-width="8" stroke-linejoin="round"';
    result = result.replace(
      new RegExp(`id="${escapedId}"([^>]*)/>`, "g"),
      `id="${svgId}"$1 fill="${color}" fill-opacity="0.94"${selectedAttributes} />`,
    );
  }

  return result;
}

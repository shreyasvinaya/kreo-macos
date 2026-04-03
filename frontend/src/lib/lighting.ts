export interface PerKeyLightingEntry {
  uiKey: string;
  label: string;
  lightPos: number;
  color: string;
}

export function buildRenderedLightingState(
  deviceKeys: PerKeyLightingEntry[],
  stagedEdits: Record<string, string>,
): PerKeyLightingEntry[] {
  return deviceKeys.map((entry) => ({
    ...entry,
    color: stagedEdits[entry.uiKey] ?? entry.color,
  }));
}

export function buildPerKeyApplyPayload(stagedEdits: Record<string, string>) {
  return {
    edits: stagedEdits,
  };
}

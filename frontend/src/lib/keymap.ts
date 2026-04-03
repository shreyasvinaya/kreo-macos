export interface KeyActionModel {
  actionId: string;
  label: string;
  category: string;
  rawValue: number;
}

export interface KeyAssignmentModel {
  uiKey: string;
  logicalId: string;
  svgId: string;
  label: string;
  protocolPos: number;
  baseAction: KeyActionModel;
  fnAction: KeyActionModel;
}

export interface KeymapModel {
  verificationStatus: string;
  assignments: KeyAssignmentModel[];
  availableActions: KeyActionModel[];
}

export interface KeymapEditPayload {
  base_raw_value?: number;
  fn_raw_value?: number;
}

const DEFAULT_KEY_COLOR = "#273240";
const REMAPPED_KEY_COLOR = "#2d6a5f";
const STAGED_KEY_COLOR = "#355c7d";

function isBaseAssignmentRemapped(assignment: KeyAssignmentModel): boolean {
  return assignment.baseAction.actionId !== `basic:${assignment.uiKey}`;
}

export function buildKeymapColorsBySvgId(
  assignments: KeyAssignmentModel[],
  stagedEdits: Record<string, KeymapEditPayload>,
): Map<string, string> {
  return new Map(
    assignments.map((assignment) => {
      if (stagedEdits[assignment.uiKey]) {
        return [assignment.svgId, STAGED_KEY_COLOR];
      }

      return [
        assignment.svgId,
        isBaseAssignmentRemapped(assignment) ? REMAPPED_KEY_COLOR : DEFAULT_KEY_COLOR,
      ];
    }),
  );
}

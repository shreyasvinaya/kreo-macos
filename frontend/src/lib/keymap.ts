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

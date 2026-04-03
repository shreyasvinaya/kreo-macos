import {
  startTransition,
  useDeferredValue,
  useEffect,
  useRef,
  useState,
  type MouseEvent,
} from "react";

import { DeviceCard } from "./components/device-card";
import { DropdownSelect } from "./components/dropdown-select";
import { TracePanel } from "./components/trace-panel";
import {
  applyGlobalLighting,
  deleteMacro,
  applySavedProfile,
  applyKeymapEdits,
  applyPerKeyLighting,
  createSavedProfile,
  loadKeyboardAsset,
  loadDashboardModel,
  loadKeymapModel,
  loadMacrosModel,
  loadPerKeyLightingModel,
  upsertMacro,
  type DashboardModel,
  type KeyboardAssetModel,
  type MacrosModel,
  type MacroSlotModel,
  type KeymapEditPayload,
  type KeymapModel,
  type PerKeyLightingModel,
} from "./lib/api";
import { buildRenderedLightingState } from "./lib/lighting";
import {
  applyCheckerPattern,
  applyRainbowPreset,
  applySolidFill,
  applyThreeColorSplit,
  applyTwoColorSplit,
} from "./lib/lighting-layout";
import {
  applyLightingColorsToSvg,
  buildKeyboardLegendOverrides,
} from "./lib/keyboard-assets";
import { buildKeymapColorsBySvgId } from "./lib/keymap";
import {
  computeNextLightingRefreshDelay,
  LIGHTING_AUTO_REFRESH_INTERVAL_MS,
  shouldAutoRefreshLighting,
} from "./lib/lighting-refresh";
import { defaultScreen, primaryNavigation, type PrimaryScreen } from "./lib/navigation";
import { buildHeaderChips, shouldShowDeviceCard } from "./lib/screen-chrome";
import { buildWorkspaceContent } from "./lib/workspace";

const initialDashboard: DashboardModel = {
  device: {
    activeProfile: "Scanning...",
    connected: false,
    configurable: false,
    dirty: false,
    firmware: "Waiting for API",
    interfaceName: "Vendor HID handshake pending",
    protocol: "bytech",
    status: "disconnected",
    supportedDevices: ["Kreo Swarm"],
    supportsProfiles: false,
    syncState: "Bootstrapping",
    targetName: "Kreo Swarm",
  },
  profiles: {
    supported: true,
    activeProfile: null,
    availableProfiles: [],
    reason: null,
    storageKind: "saved_snapshots",
    activeSnapshotId: null,
    snapshots: [],
  },
  traceEntries: [],
};

function normalizeColorInput(value: string): string | null {
  const normalized = value.trim().toLowerCase();
  if (/^#[0-9a-f]{6}$/.test(normalized)) {
    return normalized;
  }
  return null;
}

function getKeyTextColor(hexColor: string): string {
  const red = parseInt(hexColor.slice(1, 3), 16);
  const green = parseInt(hexColor.slice(3, 5), 16);
  const blue = parseInt(hexColor.slice(5, 7), 16);
  const luminance = (0.2126 * red + 0.7152 * green + 0.0722 * blue) / 255;
  return luminance > 0.65 ? "#0f1720" : "#f4f7fb";
}

const lightingModeOptions = [
  { value: "off", label: "Off" },
  { value: "static", label: "Static" },
  { value: "breathe", label: "Breathe" },
  { value: "wave", label: "Wave" },
  { value: "ripple", label: "Ripple" },
  { value: "raindrop", label: "Raindrop" },
  { value: "snake", label: "Snake" },
  { value: "converge", label: "Converge" },
  { value: "sine_wave", label: "Sine Wave" },
  { value: "kaleidoscope", label: "Kaleidoscope" },
  { value: "line_wave", label: "Line Wave" },
  { value: "laser", label: "Laser" },
  { value: "circle_wave", label: "Circle Wave" },
  { value: "dazzling", label: "Dazzling" },
  { value: "rain_down", label: "Rain Down" },
  { value: "meteor", label: "Meteor" },
  { value: "train", label: "Train" },
  { value: "fireworks", label: "Fireworks" },
];
const keyboardLegendOverrides = buildKeyboardLegendOverrides();

export function App() {
  const assetKeyboardShellRef = useRef<HTMLDivElement | null>(null);
  const [dashboard, setDashboard] = useState<DashboardModel>(initialDashboard);
  const [activeScreen, setActiveScreen] = useState<PrimaryScreen>(defaultScreen);
  const [lastSync, setLastSync] = useState("Connecting to loopback API");
  const [lightingModel, setLightingModel] = useState<PerKeyLightingModel | null>(null);
  const [keymapModel, setKeymapModel] = useState<KeymapModel | null>(null);
  const [keyboardAsset, setKeyboardAsset] = useState<KeyboardAssetModel | null>(null);
  const [keyboardSurfaceSvg, setKeyboardSurfaceSvg] = useState<string | null>(null);
  const [lightingError, setLightingError] = useState<string | null>(null);
  const [keymapError, setKeymapError] = useState<string | null>(null);
  const [keyboardAssetError, setKeyboardAssetError] = useState<string | null>(null);
  const [lightingLoading, setLightingLoading] = useState(false);
  const [keymapLoading, setKeymapLoading] = useState(false);
  const [macrosLoading, setMacrosLoading] = useState(false);
  const [keyboardAssetLoading, setKeyboardAssetLoading] = useState(false);
  const [lightingApplying, setLightingApplying] = useState(false);
  const [globalLightingApplying, setGlobalLightingApplying] = useState(false);
  const [keymapApplying, setKeymapApplying] = useState(false);
  const [macrosApplying, setMacrosApplying] = useState(false);
  const [macrosDeleting, setMacrosDeleting] = useState(false);
  const [selectedLightingKeyId, setSelectedLightingKeyId] = useState<string | null>(null);
  const [selectedKeymapKeyId, setSelectedKeymapKeyId] = useState<string | null>(null);
  const [selectedMacroSlotId, setSelectedMacroSlotId] = useState<number | null>(null);
  const [stagedLightingEdits, setStagedLightingEdits] = useState<Record<string, string>>({});
  const [stagedKeymapEdits, setStagedKeymapEdits] = useState<Record<string, KeymapEditPayload>>(
    {},
  );
  const [macrosModel, setMacrosModel] = useState<MacrosModel | null>(null);
  const [macrosError, setMacrosError] = useState<string | null>(null);
  const [macroDraftName, setMacroDraftName] = useState("New Macro");
  const [macroDraftExecutionType, setMacroDraftExecutionType] = useState("FIXED_COUNT");
  const [macroDraftCycleTimes, setMacroDraftCycleTimes] = useState("1");
  const [macroDraftBoundUiKey, setMacroDraftBoundUiKey] = useState<string | null>(null);
  const [macroDraftActions, setMacroDraftActions] = useState<
    Array<{ key: string; eventType: string; delayMs: number }>
  >([]);
  const [lightingColorInput, setLightingColorInput] = useState("#273240");
  const [solidFillColor, setSolidFillColor] = useState("#00ffaa");
  const [twoSplitLeftColor, setTwoSplitLeftColor] = useState("#ff4d4d");
  const [twoSplitRightColor, setTwoSplitRightColor] = useState("#356dff");
  const [threeSplitLeftColor, setThreeSplitLeftColor] = useState("#ff4d4d");
  const [threeSplitCenterColor, setThreeSplitCenterColor] = useState("#00ffaa");
  const [threeSplitRightColor, setThreeSplitRightColor] = useState("#356dff");
  const [checkerPrimaryColor, setCheckerPrimaryColor] = useState("#ff4d4d");
  const [checkerSecondaryColor, setCheckerSecondaryColor] = useState("#356dff");
  const [globalLightingMode, setGlobalLightingMode] = useState("custom");
  const [globalLightingBrightness, setGlobalLightingBrightness] = useState("25");
  const [globalLightingColor, setGlobalLightingColor] = useState("#00ffaa");
  const [profileNameInput, setProfileNameInput] = useState("Desk Setup");
  const [profilesError, setProfilesError] = useState<string | null>(null);
  const [profilesSaving, setProfilesSaving] = useState(false);
  const [profilesApplyingId, setProfilesApplyingId] = useState<string | null>(null);
  const [selectedSavedProfileId, setSelectedSavedProfileId] = useState<string | null>(null);
  const [isDocumentVisible, setIsDocumentVisible] = useState(
    typeof document === "undefined" ? true : document.visibilityState === "visible",
  );
  const [lastLightingInteractionAt, setLastLightingInteractionAt] = useState(() => Date.now());
  const [lastLightingRefreshAt, setLastLightingRefreshAt] = useState(() => Date.now());
  const [keyboardLegendPositions, setKeyboardLegendPositions] = useState<
    Array<{ uiKey: string; label: string; leftPercent: number; topPercent: number }>
  >([]);
  const deferredTraceEntries = useDeferredValue(dashboard.traceEntries);
  const workspaceContent = buildWorkspaceContent(activeScreen);
  const isLightingScreen = activeScreen === "Lighting";
  const isKeymapScreen = activeScreen === "Keymap";
  const isMacrosScreen = activeScreen === "Macros";
  const stagedEditCount = Object.keys(stagedLightingEdits).length;
  const stagedKeymapEditCount = Object.keys(stagedKeymapEdits).length;

  function noteLightingInteraction() {
    setLastLightingInteractionAt(Date.now());
  }

  function formatSyncTimestamp(): string {
    return new Intl.DateTimeFormat(undefined, {
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
    }).format(new Date());
  }

  function activeSavedProfileLabel(profiles: DashboardModel["profiles"]): string {
    return (
      profiles.snapshots.find((snapshot) => snapshot.snapshotId === profiles.activeSnapshotId)?.name ??
      "No saved profile"
    );
  }

  function updateDashboardProfiles(profiles: DashboardModel["profiles"]) {
    startTransition(() => {
      setDashboard((current) => ({
        ...current,
        profiles,
        device: {
          ...current.device,
          activeProfile: activeSavedProfileLabel(profiles),
        },
      }));
      setSelectedSavedProfileId((current) =>
        current && profiles.snapshots.some((snapshot) => snapshot.snapshotId === current)
          ? current
          : profiles.activeSnapshotId ?? profiles.snapshots[0]?.snapshotId ?? null,
      );
      setLastSync(formatSyncTimestamp());
    });
  }

  async function hydrateDashboardState() {
    const model = await loadDashboardModel();
    startTransition(() => {
      setDashboard(model);
      setSelectedSavedProfileId((current) =>
        current && model.profiles.snapshots.some((snapshot) => snapshot.snapshotId === current)
          ? current
          : model.profiles.activeSnapshotId ?? model.profiles.snapshots[0]?.snapshotId ?? null,
      );
      setLastSync(formatSyncTimestamp());
    });
  }

  async function hydrateLightingState() {
    setLightingLoading(true);
    setLightingError(null);

    try {
      const model = await loadPerKeyLightingModel();
      startTransition(() => {
        setLightingModel(model);
        setSelectedLightingKeyId((current) =>
          current && model.keys.some((entry) => entry.uiKey === current) ? current : null,
        );
        setLastLightingRefreshAt(Date.now());
      });
    } catch (error) {
      setLightingError(
        error instanceof Error ? error.message : "Unable to load per-key lighting state",
      );
    } finally {
      setLightingLoading(false);
    }
  }

  useEffect(() => {
    function handleVisibilityChange() {
      setIsDocumentVisible(document.visibilityState === "visible");
    }

    document.addEventListener("visibilitychange", handleVisibilityChange);
    return () => document.removeEventListener("visibilitychange", handleVisibilityChange);
  }, []);

  async function hydrateKeymapState() {
    setKeymapLoading(true);
    setKeymapError(null);

    try {
      const model = await loadKeymapModel();
      startTransition(() => {
        setKeymapModel(model);
        setSelectedKeymapKeyId((current) =>
          current && model.assignments.some((entry) => entry.uiKey === current) ? current : null,
        );
      });
    } catch (error) {
      setKeymapError(error instanceof Error ? error.message : "Unable to load keymap state");
    } finally {
      setKeymapLoading(false);
    }
  }

  async function hydrateMacrosState() {
    setMacrosLoading(true);
    setMacrosError(null);

    try {
      const model = await loadMacrosModel();
      startTransition(() => {
        setMacrosModel(model);
        setSelectedMacroSlotId((current) =>
          current !== null && model.slots.some((slot) => slot.slotId === current)
            ? current
            : model.slots[0]?.slotId ?? null,
        );
      });
    } catch (error) {
      setMacrosError(error instanceof Error ? error.message : "Unable to load macros");
    } finally {
      setMacrosLoading(false);
    }
  }

  async function hydrateKeyboardAssetSurface() {
    setKeyboardAssetLoading(true);
    setKeyboardAssetError(null);

    try {
      const asset = await loadKeyboardAsset("swarm75");
      const svgResponse = await fetch(asset.interactiveSvgUrl);
      if (!svgResponse.ok) {
        throw new Error(`interactive svg returned ${svgResponse.status}`);
      }
      const svgMarkup = await svgResponse.text();
      startTransition(() => {
        setKeyboardAsset(asset);
        setKeyboardSurfaceSvg(svgMarkup);
      });
    } catch (error) {
      setKeyboardAssetError(
        error instanceof Error ? error.message : "Unable to load keyboard assets",
      );
    } finally {
      setKeyboardAssetLoading(false);
    }
  }

  useEffect(() => {
    let cancelled = false;

    async function hydrateDashboard() {
      const model = await loadDashboardModel();
      if (cancelled) {
        return;
      }

      startTransition(() => {
        setDashboard(model);
        setSelectedSavedProfileId((current) =>
          current && model.profiles.snapshots.some((snapshot) => snapshot.snapshotId === current)
            ? current
            : model.profiles.activeSnapshotId ?? model.profiles.snapshots[0]?.snapshotId ?? null,
        );
        setLastSync(formatSyncTimestamp());
      });
    }

    void hydrateDashboard();
    const intervalId = window.setInterval(() => {
      void hydrateDashboard();
    }, 3000);

    return () => {
      cancelled = true;
      window.clearInterval(intervalId);
    };
  }, []);

  useEffect(() => {
    if (!isLightingScreen) {
      return;
    }

    let cancelled = false;

    async function loadLighting() {
      try {
        setLightingLoading(true);
        setLightingError(null);
        const model = await loadPerKeyLightingModel();
        if (cancelled) {
          return;
        }

        startTransition(() => {
          setLightingModel(model);
          setStagedLightingEdits({});
          setSelectedLightingKeyId((current) =>
            current && model.keys.some((entry) => entry.uiKey === current) ? current : null,
          );
        });
      } catch (error) {
        if (!cancelled) {
          setLightingError(
            error instanceof Error ? error.message : "Unable to load per-key lighting state",
          );
        }
      } finally {
        if (!cancelled) {
          setLightingLoading(false);
        }
      }
    }

    void loadLighting();

    return () => {
      cancelled = true;
    };
  }, [isLightingScreen]);

  useEffect(() => {
    if (!isKeymapScreen) {
      return;
    }

    let cancelled = false;

    async function loadKeymap() {
      try {
        setKeymapLoading(true);
        setKeymapError(null);
        const model = await loadKeymapModel();
        if (cancelled) {
          return;
        }

        startTransition(() => {
          setKeymapModel(model);
          setStagedKeymapEdits({});
          setSelectedKeymapKeyId((current) =>
            current && model.assignments.some((entry) => entry.uiKey === current) ? current : null,
          );
        });
      } catch (error) {
        if (!cancelled) {
          setKeymapError(error instanceof Error ? error.message : "Unable to load keymap state");
        }
      } finally {
        if (!cancelled) {
          setKeymapLoading(false);
        }
      }
    }

    void loadKeymap();

    return () => {
      cancelled = true;
    };
  }, [isKeymapScreen]);

  useEffect(() => {
    if ((!isLightingScreen && !isKeymapScreen && !isMacrosScreen) || (keyboardAsset && keyboardSurfaceSvg)) {
      return;
    }

    void hydrateKeyboardAssetSurface();
  }, [isLightingScreen, isKeymapScreen, isMacrosScreen, keyboardAsset, keyboardSurfaceSvg]);

  useEffect(() => {
    if (!isMacrosScreen) {
      return;
    }

    let cancelled = false;

    async function loadMacros() {
      try {
        setMacrosLoading(true);
        setMacrosError(null);
        const model = await loadMacrosModel();
        if (cancelled) {
          return;
        }
        startTransition(() => {
          setMacrosModel(model);
          setSelectedMacroSlotId((current) =>
            current !== null && model.slots.some((slot) => slot.slotId === current)
              ? current
              : model.slots[0]?.slotId ?? null,
          );
        });
      } catch (error) {
        if (!cancelled) {
          setMacrosError(error instanceof Error ? error.message : "Unable to load macros");
        }
      } finally {
        if (!cancelled) {
          setMacrosLoading(false);
        }
      }
    }

    void loadMacros();

    return () => {
      cancelled = true;
    };
  }, [isMacrosScreen]);

  useEffect(() => {
    if (
      !shouldAutoRefreshLighting({
        isLightingScreen,
        stagedEditCount,
        isDocumentVisible,
      })
    ) {
      return;
    }

    const timeoutId = window.setTimeout(() => {
      void hydrateLightingState();
    }, computeNextLightingRefreshDelay({
      now: Date.now(),
      lastRefreshAt: lastLightingRefreshAt,
      lastInteractionAt: lastLightingInteractionAt,
    }));

    return () => window.clearTimeout(timeoutId);
  }, [isLightingScreen, stagedEditCount, isDocumentVisible, lastLightingInteractionAt, lastLightingRefreshAt]);

  const renderedLightingKeys =
    isLightingScreen && lightingModel
      ? buildRenderedLightingState(lightingModel.keys, stagedLightingEdits)
      : [];
  const lightingKeyMap = new Map(renderedLightingKeys.map((entry) => [entry.uiKey, entry]));
  const keymapAssignments = keymapModel?.assignments ?? [];
  const keymapAssignmentMap = new Map(keymapAssignments.map((entry) => [entry.uiKey, entry]));
  const selectedLightingKey = selectedLightingKeyId
    ? lightingKeyMap.get(selectedLightingKeyId) ?? null
    : null;
  const selectedKeymapAssignment = selectedKeymapKeyId
    ? keymapAssignmentMap.get(selectedKeymapKeyId) ?? null
    : null;
  const selectedSavedProfile = selectedSavedProfileId
    ? dashboard.profiles.snapshots.find((snapshot) => snapshot.snapshotId === selectedSavedProfileId) ??
      null
    : null;
  const selectedLightingDisplayLabel =
    (selectedLightingKeyId ? keyboardAsset?.keysByUiKey.get(selectedLightingKeyId)?.label : null) ??
    selectedLightingKey?.label ??
    "Key";
  const selectedLightingSvgId = selectedLightingKeyId
    ? keyboardAsset?.keysByUiKey.get(selectedLightingKeyId)?.svgId ?? null
    : null;
  const selectedKeymapSvgId = selectedKeymapKeyId
    ? keyboardAsset?.keysByUiKey.get(selectedKeymapKeyId)?.svgId ?? null
    : null;
  const selectedKeymapBaseRawValue =
    selectedKeymapAssignment &&
    stagedKeymapEdits[selectedKeymapAssignment.uiKey]?.base_raw_value !== undefined
      ? stagedKeymapEdits[selectedKeymapAssignment.uiKey]?.base_raw_value
      : selectedKeymapAssignment?.baseAction.rawValue;
  const selectedKeymapFnRawValue =
    selectedKeymapAssignment &&
    stagedKeymapEdits[selectedKeymapAssignment.uiKey]?.fn_raw_value !== undefined
      ? stagedKeymapEdits[selectedKeymapAssignment.uiKey]?.fn_raw_value
      : selectedKeymapAssignment?.fnAction.rawValue;
  const selectedMacroSlot =
    selectedMacroSlotId !== null
      ? macrosModel?.slots.find((slot) => slot.slotId === selectedMacroSlotId) ?? null
      : null;
  const macroBoundUiKeys = new Set(
    (macrosModel?.slots ?? []).flatMap((slot) => slot.boundUiKeys),
  );
  const selectedMacroBoundUiKeys = new Set(selectedMacroSlot?.boundUiKeys ?? []);
  const selectedMacroSvgId =
    macroDraftBoundUiKey ? keyboardAsset?.keysByUiKey.get(macroDraftBoundUiKey)?.svgId ?? null : null;
  const macroKeyOptions = keyboardAsset?.keys ?? [];
  const profileDropdownOptions = dashboard.profiles.snapshots.map((snapshot) => ({
    value: snapshot.snapshotId,
    label: snapshot.name,
    meta:
      dashboard.profiles.activeSnapshotId === snapshot.snapshotId
        ? "Active saved profile"
        : new Date(snapshot.updatedAt).toLocaleString(),
  }));
  const lightingModeDropdownOptions = lightingModeOptions.map((option) => ({
    value: option.value,
    label: option.label,
  }));
  const keymapDropdownOptions =
    keymapModel?.availableActions.map((action) => ({
      value: String(action.rawValue),
      label: action.label,
      meta: action.category,
    })) ?? [];
  const macroSlotDropdownOptions = [
    ...(macrosModel?.slots.map((slot) => ({
      value: String(slot.slotId),
      label: `Slot ${slot.slotId + 1}`,
      meta: slot.name,
    })) ?? []),
    ...((macrosModel?.nextSlotId ?? 0) < (macrosModel?.maxSlots ?? 0)
      ? [
          {
            value: "new",
            label: `New slot ${((macrosModel?.nextSlotId ?? 0) + 1).toString()}`,
            meta: "Create a new macro slot",
          },
        ]
      : []),
  ];
  const macroExecutionOptions = [
    { value: "FIXED_COUNT", label: "Fixed Count" },
    { value: "UNTIL_ANY_PRESSED", label: "Until Any Pressed" },
    { value: "UNTIL_RELEASED", label: "Until Released" },
  ];
  const macroKeyDropdownOptions = macroKeyOptions.map((key) => ({
    value: key.uiKey,
    label: key.label,
    meta: key.logicalId,
  }));
  const macroEventOptions = [
    { value: "press", label: "Press" },
    { value: "release", label: "Release" },
  ];

  useEffect(() => {
    if (selectedLightingKey) {
      setLightingColorInput(selectedLightingKey.color);
    }
  }, [selectedLightingKey]);

  useEffect(() => {
    if (!lightingModel) {
      return;
    }
    setGlobalLightingMode(lightingModel.mode);
    setGlobalLightingBrightness(String(lightingModel.brightness));
    if (lightingModel.mode === "static") {
      setGlobalLightingColor(lightingModel.keys[0]?.color ?? "#00ffaa");
    }
  }, [lightingModel]);

  useEffect(() => {
    if (!isMacrosScreen) {
      return;
    }

    if (selectedMacroSlot) {
      setMacroDraftName(selectedMacroSlot.name);
      setMacroDraftExecutionType(selectedMacroSlot.executionType);
      setMacroDraftCycleTimes(String(selectedMacroSlot.cycleTimes));
      setMacroDraftBoundUiKey(selectedMacroSlot.boundUiKeys[0] ?? null);
      setMacroDraftActions(
        selectedMacroSlot.actions.map((action) => ({
          key: action.key,
          eventType: action.eventType,
          delayMs: action.delayMs,
        })),
      );
      return;
    }

    setMacroDraftName("New Macro");
    setMacroDraftExecutionType("FIXED_COUNT");
    setMacroDraftCycleTimes("1");
    setMacroDraftBoundUiKey(null);
    setMacroDraftActions([]);
  }, [isMacrosScreen, selectedMacroSlot]);

  const effectiveDashboard: DashboardModel = {
    ...dashboard,
    device: {
      ...dashboard.device,
      dirty: dashboard.device.dirty || stagedEditCount > 0 || stagedKeymapEditCount > 0,
    },
  };
  const connectionLabel =
    effectiveDashboard.device.status === "connected" ? "Connected" : "Disconnected";
  const headerChips = buildHeaderChips(activeScreen, {
    activeProfile: effectiveDashboard.device.activeProfile,
    connectionLabel,
    firmware: effectiveDashboard.device.firmware,
    syncState: effectiveDashboard.device.syncState,
  });
  const eventCounts = dashboard.traceEntries.reduce(
    (counts, entry) => ({
      ...counts,
      [entry.direction]: counts[entry.direction] + 1,
    }),
    { read: 0, write: 0, meta: 0 },
  );

  function handleSelectLightingKey(keyId: string) {
    if (!lightingKeyMap.has(keyId)) {
      return;
    }
    noteLightingInteraction();
    setSelectedLightingKeyId(keyId);
  }

  function handleLightingColorChange(nextColor: string) {
    if (!selectedLightingKey) {
      return;
    }

    noteLightingInteraction();
    setLightingColorInput(nextColor.toLowerCase());
    const normalized = normalizeColorInput(nextColor);
    if (!normalized) {
      return;
    }

    setStagedLightingEdits((current) => ({
      ...current,
      [selectedLightingKey.uiKey]: normalized,
    }));
  }

  function handleBoardPreset(edits: Record<string, string>) {
    noteLightingInteraction();
    setStagedLightingEdits(edits);
  }

  async function handleApplyLighting() {
    if (stagedEditCount === 0) {
      return;
    }

    noteLightingInteraction();
    setLightingApplying(true);
    setLightingError(null);

    try {
      const model = await applyPerKeyLighting(stagedLightingEdits);
      startTransition(() => {
        setLightingModel(model);
        setStagedLightingEdits({});
        setSelectedLightingKeyId((current) =>
          current && model.keys.some((entry) => entry.uiKey === current) ? current : null,
        );
      });
    } catch (error) {
      setLightingError(
        error instanceof Error ? error.message : "Unable to apply staged per-key edits",
      );
    } finally {
      setLightingApplying(false);
    }
  }

  async function handleResetLighting() {
    noteLightingInteraction();
    setStagedLightingEdits({});
    await hydrateLightingState();
  }

  async function handleApplyGlobalLighting() {
    if (!lightingModel) {
      return;
    }

    noteLightingInteraction();
    setGlobalLightingApplying(true);
    setLightingError(null);

    try {
      await applyGlobalLighting({
        mode: globalLightingMode,
        brightness: Number(globalLightingBrightness),
        color:
          globalLightingMode === "static"
            ? normalizeColorInput(globalLightingColor)
            : null,
      });
      await hydrateLightingState();
    } catch (error) {
      setLightingError(error instanceof Error ? error.message : "Unable to apply lighting effect");
    } finally {
      setGlobalLightingApplying(false);
    }
  }

  function handleSelectKeymapKey(keyId: string) {
    if (!keymapAssignmentMap.has(keyId)) {
      return;
    }
    setSelectedKeymapKeyId(keyId);
  }

  function handleKeymapActionChange(
    uiKey: string,
    field: "base_raw_value" | "fn_raw_value",
    rawValue: number,
  ) {
    setStagedKeymapEdits((current) => ({
      ...current,
      [uiKey]: {
        ...current[uiKey],
        [field]: rawValue,
      },
    }));
  }

  async function handleApplyKeymap() {
    if (stagedKeymapEditCount === 0) {
      return;
    }

    setKeymapApplying(true);
    setKeymapError(null);

    try {
      const model = await applyKeymapEdits(stagedKeymapEdits);
      startTransition(() => {
        setKeymapModel(model);
        setStagedKeymapEdits({});
        setSelectedKeymapKeyId((current) =>
          current && model.assignments.some((entry) => entry.uiKey === current) ? current : null,
        );
      });
    } catch (error) {
      setKeymapError(error instanceof Error ? error.message : "Unable to apply staged keymap edits");
    } finally {
      setKeymapApplying(false);
    }
  }

  async function handleResetKeymap() {
    setStagedKeymapEdits({});
    await hydrateKeymapState();
  }

  async function handleCreateProfile() {
    const name = profileNameInput.trim();
    if (!name) {
      setProfilesError("Profile name is required");
      return;
    }

    setProfilesSaving(true);
    setProfilesError(null);

    try {
      const profiles = await createSavedProfile(name);
      updateDashboardProfiles(profiles);
    } catch (error) {
      setProfilesError(error instanceof Error ? error.message : "Unable to save current profile");
    } finally {
      setProfilesSaving(false);
    }
  }

  async function handleApplyProfile(snapshotId: string) {
    setProfilesApplyingId(snapshotId);
    setProfilesError(null);

    try {
      setStagedLightingEdits({});
      setStagedKeymapEdits({});
      const profiles = await applySavedProfile(snapshotId);
      updateDashboardProfiles(profiles);
      if (activeScreen === "Lighting") {
        await hydrateLightingState();
      }
      if (activeScreen === "Keymap") {
        await hydrateKeymapState();
      }
    } catch (error) {
      setProfilesError(error instanceof Error ? error.message : "Unable to apply saved profile");
    } finally {
      setProfilesApplyingId(null);
    }
  }

  function handleCreateNewMacroDraft() {
    setSelectedMacroSlotId(null);
    setMacroDraftName("New Macro");
    setMacroDraftExecutionType("FIXED_COUNT");
    setMacroDraftCycleTimes("1");
    setMacroDraftBoundUiKey(null);
    setMacroDraftActions([]);
  }

  function handleMacroActionChange(
    index: number,
    field: "key" | "eventType" | "delayMs",
    value: string | number,
  ) {
    setMacroDraftActions((current) =>
      current.map((action, actionIndex) =>
        actionIndex === index ? { ...action, [field]: value } : action,
      ),
    );
  }

  function handleAddMacroAction() {
    setMacroDraftActions((current) => [
      ...current,
      { key: "a", eventType: "press", delayMs: 0 },
    ]);
  }

  function handleRemoveMacroAction(index: number) {
    setMacroDraftActions((current) => current.filter((_, actionIndex) => actionIndex !== index));
  }

  async function handleSaveMacro() {
    if (!macrosModel) {
      return;
    }

    const slotId = selectedMacroSlotId ?? macrosModel.nextSlotId;
    setMacrosApplying(true);
    setMacrosError(null);

    try {
      const model = await upsertMacro(slotId, {
        name: macroDraftName.trim() || `Macro ${slotId + 1}`,
        boundUiKey: macroDraftBoundUiKey,
        executionType: macroDraftExecutionType,
        cycleTimes: Number(macroDraftCycleTimes) || 1,
        actions: macroDraftActions,
      });
      startTransition(() => {
        setMacrosModel(model);
        setSelectedMacroSlotId(slotId);
      });
    } catch (error) {
      setMacrosError(error instanceof Error ? error.message : "Unable to save macro");
    } finally {
      setMacrosApplying(false);
    }
  }

  async function handleDeleteMacro() {
    if (selectedMacroSlotId === null) {
      return;
    }

    setMacrosDeleting(true);
    setMacrosError(null);

    try {
      const model = await deleteMacro(selectedMacroSlotId);
      startTransition(() => {
        setMacrosModel(model);
        setSelectedMacroSlotId(model.slots[0]?.slotId ?? null);
      });
    } catch (error) {
      setMacrosError(error instanceof Error ? error.message : "Unable to delete macro");
    } finally {
      setMacrosDeleting(false);
    }
  }

  function handleKeyboardSurfaceClick(event: MouseEvent<HTMLDivElement>) {
    if (!keyboardAsset) {
      return;
    }

    const target = event.target;
    if (!(target instanceof Element)) {
      return;
    }

    const keyElement = target.closest("[id^='key_']");
    if (!(keyElement instanceof Element)) {
      return;
    }

    const svgId = keyElement.getAttribute("id");
    if (!svgId) {
      return;
    }

    const assetKey = keyboardAsset.keysBySvgId.get(svgId);
    if (!assetKey) {
      return;
    }

    if (isLightingScreen && lightingKeyMap.has(assetKey.uiKey)) {
      handleSelectLightingKey(assetKey.uiKey);
      return;
    }

    if (isKeymapScreen && keymapAssignmentMap.has(assetKey.uiKey)) {
      handleSelectKeymapKey(assetKey.uiKey);
      return;
    }

    if (isMacrosScreen) {
      setMacroDraftBoundUiKey(assetKey.uiKey);
    }
  }

  const lightingColorsBySvgId = new Map<string, string>();
  if (keyboardAsset) {
    for (const entry of renderedLightingKeys) {
      const assetKey = keyboardAsset.keysByUiKey.get(entry.uiKey);
      if (assetKey) {
        lightingColorsBySvgId.set(assetKey.svgId, entry.color);
      }
    }
  }
  const renderedKeyboardSurfaceSvg =
    keyboardSurfaceSvg && keyboardAsset && isLightingScreen
      ? applyLightingColorsToSvg(keyboardSurfaceSvg, lightingColorsBySvgId, selectedLightingSvgId)
      : keyboardSurfaceSvg && keyboardAsset && isKeymapScreen
        ? applyLightingColorsToSvg(
            keyboardSurfaceSvg,
            buildKeymapColorsBySvgId(keymapAssignments, stagedKeymapEdits),
            selectedKeymapSvgId,
          )
        : keyboardSurfaceSvg && keyboardAsset && isMacrosScreen
        ? applyLightingColorsToSvg(
            keyboardSurfaceSvg,
            new Map(
              keyboardAsset.keys
                .filter((entry) => macroBoundUiKeys.has(entry.uiKey) || selectedMacroBoundUiKeys.has(entry.uiKey))
                .map((entry) => [
                  entry.svgId,
                  selectedMacroBoundUiKeys.has(entry.uiKey) ? "#ff9f1c" : "#355c7d",
                ]),
            ),
            selectedMacroSvgId,
          )
      : null;

  const refreshStateLabel =
    stagedEditCount > 0
      ? "Refresh paused while dirty"
      : !isDocumentVisible
        ? "Refresh paused in background"
        : `Idle refresh every ${LIGHTING_AUTO_REFRESH_INTERVAL_MS / 1000}s`;
  const pageGridClass =
    activeScreen === "Lighting" || activeScreen === "Keymap" || activeScreen === "Macros"
      ? "page-grid lighting-grid"
      : activeScreen === "Device"
        ? "page-grid device-grid"
        : activeScreen === "Events"
          ? "page-grid events-grid"
          : "page-grid standard-grid";

  useEffect(() => {
    const shell = assetKeyboardShellRef.current;
    if (!shell || !keyboardAsset || !renderedKeyboardSurfaceSvg) {
      setKeyboardLegendPositions([]);
      return;
    }
    const currentKeyboardAsset = keyboardAsset;

    let cancelled = false;

    function computeLegendPositions() {
      const currentShell = assetKeyboardShellRef.current;
      if (!currentShell) {
        return;
      }

      const svg = currentShell.querySelector(".asset-keyboard-rgb svg");
      if (!(svg instanceof SVGSVGElement)) {
        return;
      }

      const shellRect = currentShell.getBoundingClientRect();
      const nextPositions = keyboardLegendOverrides.flatMap((override) => {
        const assetKey = currentKeyboardAsset.keysByUiKey.get(override.uiKey);
        if (!assetKey) {
          return [];
        }

        const selector = `#${assetKey.svgId.replace(/[ !"#$%&'()*+,./:;<=>?@[\\\]^`{|}~]/g, "\\$&")}`;
        const keyElement = svg.querySelector(selector);
        if (!(keyElement instanceof SVGGraphicsElement)) {
          return [];
        }

        const rect = keyElement.getBoundingClientRect();
        return [
          {
            uiKey: override.uiKey,
            label: override.label,
            leftPercent: (((rect.left - shellRect.left) + rect.width / 2) / shellRect.width) * 100,
            topPercent: (((rect.top - shellRect.top) + rect.height * 0.78) / shellRect.height) * 100,
          },
        ];
      });

      if (!cancelled) {
        setKeyboardLegendPositions(nextPositions);
      }
    }

    const frameId = window.requestAnimationFrame(computeLegendPositions);
    window.addEventListener("resize", computeLegendPositions);

    return () => {
      cancelled = true;
      window.cancelAnimationFrame(frameId);
      window.removeEventListener("resize", computeLegendPositions);
    };
  }, [keyboardAsset, renderedKeyboardSurfaceSvg]);

  function renderAssetKeyboardShell(ariaLabel: string) {
    return (
      <div className="asset-keyboard-shell" ref={assetKeyboardShellRef}>
        <img
          alt=""
          aria-hidden="true"
          className="asset-keyboard-layer asset-keyboard-base"
          src={keyboardAsset?.baseImageUrl}
        />
        <div
          aria-label={ariaLabel}
          className="asset-keyboard-layer asset-keyboard-rgb"
          onClick={handleKeyboardSurfaceClick}
          dangerouslySetInnerHTML={{ __html: renderedKeyboardSurfaceSvg ?? "" }}
        />
        <img
          alt=""
          aria-hidden="true"
          className="asset-keyboard-layer asset-keyboard-letters"
          src={keyboardAsset?.lettersImageUrl}
        />
        <div aria-hidden="true" className="asset-keyboard-layer asset-keyboard-legends">
          {keyboardLegendPositions.map((entry) => (
            <span
              className="asset-keyboard-legend"
              key={entry.uiKey}
              style={{ left: `${entry.leftPercent}%`, top: `${entry.topPercent}%` }}
            >
              {entry.label}
            </span>
          ))}
        </div>
      </div>
    );
  }

  return (
    <main className="launcher-shell">
      <aside className="sidebar">
        <div className="sidebar-brand">
          <p className="sidebar-kicker">Kreo Kontrol</p>
          <strong>{effectiveDashboard.device.targetName}</strong>
          <span>{effectiveDashboard.device.protocol.toUpperCase()} / macOS</span>
        </div>

        <nav aria-label="Primary" className="sidebar-nav">
          {primaryNavigation.map((item) => (
            <button
              className={`sidebar-item ${activeScreen === item ? "sidebar-item-active" : ""}`}
              key={item}
              onClick={() => setActiveScreen(item)}
              type="button"
            >
              {item}
            </button>
          ))}
        </nav>

        <div className="sidebar-footer">
          <span className={`status-pill status-${effectiveDashboard.device.status}`}>
            {effectiveDashboard.device.status === "connected" ? "Connected" : "Disconnected"}
          </span>
          <p>Last sync {lastSync}</p>
        </div>
      </aside>

      <section className="workspace">
        <header className="workspace-header">
          <div>
            <p className="panel-kicker">{workspaceContent.headerKicker}</p>
            <h1>{workspaceContent.headerTitle}</h1>
          </div>

          <div className="header-summary">
            {headerChips.map((chip, index) => {
              if (chip.kind === "connection") {
                return (
                  <span
                    className={`status-pill status-${effectiveDashboard.device.status}`}
                    key={`${chip.kind}-${index}`}
                  >
                    {chip.label}
                  </span>
                );
              }

              if (chip.kind === "profile") {
                return (
                  <DropdownSelect
                    ariaLabel="Apply saved profile"
                    disabled={profileDropdownOptions.length === 0 || profilesApplyingId !== null}
                    key={`${chip.kind}-${index}`}
                    onChange={(snapshotId) => void handleApplyProfile(snapshotId)}
                    options={profileDropdownOptions}
                    placeholderLabel={
                      profilesApplyingId !== null ? "Applying..." : chip.label
                    }
                    value={dashboard.profiles.activeSnapshotId}
                    variant="pill"
                  />
                );
              }

              return (
                <span className="header-chip" key={`${chip.kind}-${index}`}>
                  {chip.label}
                </span>
              );
            })}
          </div>
        </header>

        <div className={pageGridClass}>
          <section className="main-column">
            {shouldShowDeviceCard(activeScreen) ? (
              <DeviceCard device={effectiveDashboard.device} />
            ) : null}
            {activeScreen === "Lighting" ? (
              <section className="panel keyboard-workspace lighting-keyboard-panel">
                <div className="panel-header compact-header">
                  <div>
                    <p className="panel-kicker">Keyboard</p>
                    <h2>{workspaceContent.keyboardTitle}</h2>
                  </div>
                  <span className="selection-pill">{`${stagedEditCount} staged edits`}</span>
                </div>

                <div className="keyboard-frame realistic-frame board-frame">
                  {lightingError || keyboardAssetError ? (
                    <div className="lighting-empty-state">
                      <strong>Lighting session unavailable</strong>
                      <p>{lightingError ?? keyboardAssetError}</p>
                    </div>
                  ) : lightingLoading || keyboardAssetLoading || !renderedKeyboardSurfaceSvg || !keyboardAsset ? (
                    <div className="lighting-empty-state">
                      <strong>Loading keyboard surface</strong>
                      <p>Fetching the vendored Swarm75 assets and live lighting state.</p>
                    </div>
                  ) : (
                    renderAssetKeyboardShell("Lighting editor keyboard")
                  )}
                </div>
              </section>
            ) : activeScreen === "Keymap" ? (
              <section className="panel keyboard-workspace lighting-keyboard-panel">
                <div className="panel-header compact-header">
                  <div>
                    <p className="panel-kicker">Keyboard</p>
                    <h2>{workspaceContent.keyboardTitle}</h2>
                  </div>
                  <span className="selection-pill">{`${stagedKeymapEditCount} staged edits`}</span>
                </div>

                <div className="keyboard-frame realistic-frame board-frame">
                  {keymapError || keyboardAssetError ? (
                    <div className="lighting-empty-state">
                      <strong>Keymap session unavailable</strong>
                      <p>{keymapError ?? keyboardAssetError}</p>
                    </div>
                  ) : keymapLoading || keyboardAssetLoading || !renderedKeyboardSurfaceSvg || !keyboardAsset ? (
                    <div className="lighting-empty-state">
                      <strong>Loading keyboard surface</strong>
                      <p>Fetching the vendored Swarm75 assets and live key assignments.</p>
                    </div>
                  ) : (
                    renderAssetKeyboardShell("Keymap editor keyboard")
                  )}
                </div>
              </section>
            ) : activeScreen === "Macros" ? (
              <section className="panel keyboard-workspace lighting-keyboard-panel">
                <div className="panel-header compact-header">
                  <div>
                    <p className="panel-kicker">Keyboard</p>
                    <h2>{workspaceContent.keyboardTitle}</h2>
                  </div>
                  <span className="selection-pill">
                    {macrosModel?.supported ? `${macrosModel.slots.length} macros` : "Wired only"}
                  </span>
                </div>

                <div className="keyboard-frame realistic-frame board-frame">
                  {macrosError || keyboardAssetError ? (
                    <div className="lighting-empty-state">
                      <strong>Macro session unavailable</strong>
                      <p>{macrosError ?? keyboardAssetError}</p>
                    </div>
                  ) : macrosLoading || keyboardAssetLoading || !renderedKeyboardSurfaceSvg || !keyboardAsset ? (
                    <div className="lighting-empty-state">
                      <strong>Loading keyboard surface</strong>
                      <p>Fetching the vendored Swarm75 assets and wired macro state.</p>
                    </div>
                  ) : !macrosModel?.supported ? (
                    <div className="lighting-empty-state">
                      <strong>Macros unavailable</strong>
                      <p>{macrosModel?.reason ?? "Macros require wired USB mode on this keyboard."}</p>
                    </div>
                  ) : (
                    renderAssetKeyboardShell("Macros editor keyboard")
                  )}
                </div>
              </section>
            ) : activeScreen === "Device" ? (
              <section className="panel device-details-panel">
                <div className="panel-header compact-header">
                  <div>
                    <p className="panel-kicker">Hardware</p>
                    <h2>Technical Details</h2>
                  </div>
                  <span className={`status-pill status-${effectiveDashboard.device.status}`}>
                    {connectionLabel}
                  </span>
                </div>

                <div className="summary-grid">
                  <div>
                    <span className="meta-label">Target</span>
                    <strong>{effectiveDashboard.device.targetName}</strong>
                  </div>
                  <div>
                    <span className="meta-label">Protocol</span>
                    <strong>{effectiveDashboard.device.protocol}</strong>
                  </div>
                  <div>
                    <span className="meta-label">Interface</span>
                    <strong>{effectiveDashboard.device.interfaceName}</strong>
                  </div>
                  <div>
                    <span className="meta-label">Firmware</span>
                    <strong>{effectiveDashboard.device.firmware}</strong>
                  </div>
                  <div>
                    <span className="meta-label">Active Profile</span>
                    <strong>{effectiveDashboard.device.activeProfile}</strong>
                  </div>
                  <div>
                    <span className="meta-label">Sync</span>
                    <strong>{effectiveDashboard.device.syncState}</strong>
                  </div>
                </div>

                <div className="summary-foot">
                  <div className="signal-block compact-signal">
                    <span className="meta-label">Supported Devices</span>
                    <strong>{effectiveDashboard.device.supportedDevices.join(", ")}</strong>
                  </div>
                  <div className="signal-block compact-signal">
                    <span className="meta-label">Lighting Capability</span>
                    <strong>
                      {lightingModel?.perKeyRgbSupported ? "Per-key RGB supported" : "Load Lighting to inspect"}
                    </strong>
                  </div>
                </div>
              </section>
            ) : activeScreen === "Profiles" ? (
              <section className="panel generic-page-panel">
                <div className="panel-header compact-header">
                  <div>
                    <p className="panel-kicker">{workspaceContent.headerKicker}</p>
                    <h2>{workspaceContent.keyboardTitle}</h2>
                  </div>
                  <span className="selection-pill">{dashboard.profiles.snapshots.length} saved</span>
                </div>

                <div className="profiles-toolbar">
                  <label className="hex-control profile-name-control">
                    <span className="meta-label">Save current keyboard state as</span>
                    <input
                      onChange={(event) => setProfileNameInput(event.target.value)}
                      placeholder="Desk Setup"
                      type="text"
                      value={profileNameInput}
                    />
                  </label>
                  <button disabled={profilesSaving} onClick={() => void handleCreateProfile()} type="button">
                    {profilesSaving ? "Saving..." : "Save current state"}
                  </button>
                </div>

                {profilesError ? <p className="profile-error">{profilesError}</p> : null}

                {dashboard.profiles.snapshots.length > 0 ? (
                  <div className="profiles-list">
                    {dashboard.profiles.snapshots.map((snapshot) => (
                      <button
                        className={`profile-card ${selectedSavedProfileId === snapshot.snapshotId ? "profile-card-active" : ""}`}
                        key={snapshot.snapshotId}
                        onClick={() => setSelectedSavedProfileId(snapshot.snapshotId)}
                        type="button"
                      >
                        <div className="profile-card-header">
                          <strong>{snapshot.name}</strong>
                          {dashboard.profiles.activeSnapshotId === snapshot.snapshotId ? (
                            <span className="selection-pill subtle-pill">Active</span>
                          ) : null}
                        </div>
                        <div className="profile-card-meta">
                          <span>{snapshot.lighting.mode}</span>
                          <span>{Object.keys(snapshot.lighting.keys).length} lit keys</span>
                          <span>{Object.keys(snapshot.keymap.assignments).length} mapped keys</span>
                        </div>
                        <div className="profile-card-actions">
                          <span>{new Date(snapshot.updatedAt).toLocaleString()}</span>
                          <span className="secondary-link">Open details</span>
                        </div>
                      </button>
                    ))}
                  </div>
                ) : (
                  <div className="lighting-empty-state generic-page-empty">
                    <strong>No saved profiles yet</strong>
                    <p>Save the current lighting and keymap state to create your first reusable snapshot.</p>
                  </div>
                )}
              </section>
            ) : activeScreen === "Events" ? (
              <TracePanel entries={deferredTraceEntries} />
            ) : (
              <section className="panel generic-page-panel">
                <div className="panel-header compact-header">
                  <div>
                    <p className="panel-kicker">{workspaceContent.headerKicker}</p>
                    <h2>{workspaceContent.keyboardTitle}</h2>
                  </div>
                  <span className="selection-pill">{workspaceContent.selectionLabel}</span>
                </div>
                <div className="lighting-empty-state generic-page-empty">
                  <strong>{workspaceContent.headerTitle}</strong>
                  <p>Use this page for its dedicated editor surface. Device details and event logs now live in their own pages.</p>
                </div>
              </section>
            )}
          </section>

          <aside className="inspector-column">
            {activeScreen === "Lighting" ? (
              <>
                <section className="panel inspector-panel">
                  <div className="panel-header compact-header">
                    <div>
                      <p className="panel-kicker">Selected Key</p>
                      <h2>{workspaceContent.inspectorTitle}</h2>
                    </div>
                    <span className="selection-pill subtle-pill">Per-key RGB</span>
                  </div>

                  <div className="lighting-meta-row">
                    <span>{lightingModel?.mode ?? (lightingLoading ? "Loading" : "Unavailable")}</span>
                    <span>{lightingModel ? `${lightingModel.brightness}% brightness` : "..."}</span>
                    <span>{refreshStateLabel}</span>
                  </div>

                  {selectedLightingKey ? (
                    <>
                      <div className="inspector-key">
                        <div
                          className="preview-keycap"
                          style={{
                            backgroundColor: selectedLightingKey.color,
                            color: getKeyTextColor(selectedLightingKey.color),
                          }}
                        >
                          {selectedLightingDisplayLabel}
                        </div>
                        <div>
                          <strong>{selectedLightingDisplayLabel}</strong>
                          <p>light_pos {selectedLightingKey.lightPos}</p>
                        </div>
                      </div>

                      <div className="lighting-controls">
                        <label className="color-control">
                          <span className="meta-label">Selected key color</span>
                          <input
                            onChange={(event) => handleLightingColorChange(event.target.value)}
                            type="color"
                            value={normalizeColorInput(lightingColorInput) ?? selectedLightingKey.color}
                          />
                        </label>

                        <label className="hex-control">
                          <span className="meta-label">Hex</span>
                          <input
                            onChange={(event) => handleLightingColorChange(event.target.value)}
                            type="text"
                            value={lightingColorInput}
                          />
                        </label>
                      </div>
                    </>
                  ) : (
                    <div className="lighting-empty-state lighting-empty-panel">
                      <strong>Select a key</strong>
                      <p>Choose any bright key on the board to edit its staged color.</p>
                    </div>
                  )}

                  <div className="inspector-actions">
                    <button
                      disabled={stagedEditCount === 0 || lightingApplying}
                      onClick={() => void handleApplyLighting()}
                      type="button"
                    >
                      {lightingApplying ? "Applying..." : "Apply staged edits"}
                    </button>
                    <button
                      className="secondary-button"
                      disabled={stagedEditCount === 0}
                      onClick={() => void handleResetLighting()}
                      type="button"
                    >
                      Reset
                    </button>
                  </div>
                </section>

                <section className="panel board-actions-panel">
                <div className="panel-header compact-header board-actions-header">
                  <div>
                    <p className="panel-kicker">Board Actions</p>
                    <h2>Quick fills and combinations</h2>
                  </div>
                </div>

                <section className="board-actions">
                  <div className="board-action-group">
                    <span className="meta-label">Preset Lighting</span>
                    <div className="preset-controls">
                      <label className="select-control">
                        <span className="meta-label">Mode</span>
                        <DropdownSelect
                          ariaLabel="Select lighting mode"
                          onChange={(value) => {
                            noteLightingInteraction();
                            setGlobalLightingMode(value);
                          }}
                          options={lightingModeDropdownOptions}
                          value={globalLightingMode}
                        />
                      </label>
                      <label className="select-control">
                        <span className="meta-label">Brightness</span>
                        <input
                          max="100"
                          min="0"
                          onChange={(event) => {
                            noteLightingInteraction();
                            setGlobalLightingBrightness(event.target.value);
                          }}
                          step="5"
                          type="range"
                          value={globalLightingBrightness}
                        />
                        <span className="meta-label">{globalLightingBrightness}%</span>
                      </label>
                      {globalLightingMode === "static" ? (
                        <label className="color-control">
                          <span className="meta-label">Static color</span>
                          <input
                            onChange={(event) => {
                              noteLightingInteraction();
                              setGlobalLightingColor(event.target.value);
                            }}
                            type="color"
                            value={normalizeColorInput(globalLightingColor) ?? "#00ffaa"}
                          />
                        </label>
                      ) : null}
                      <button
                        disabled={globalLightingApplying || stagedEditCount > 0}
                        onClick={() => void handleApplyGlobalLighting()}
                        type="button"
                      >
                        {globalLightingApplying ? "Applying..." : "Apply effect"}
                      </button>
                    </div>
                  </div>

                  <div className="board-action-group">
                    <span className="meta-label">Solid Fill</span>
                    <div className="board-action-row">
                      <input
                        onChange={(event) => setSolidFillColor(event.target.value)}
                        type="color"
                        value={solidFillColor}
                      />
                      <button
                        disabled={!lightingModel}
                        onClick={() =>
                          lightingModel &&
                          handleBoardPreset(applySolidFill(lightingModel.keys, solidFillColor))
                        }
                        type="button"
                      >
                        Fill
                      </button>
                    </div>
                  </div>

                  <div className="board-action-group">
                    <span className="meta-label">Two-Color Split</span>
                    <div className="board-action-row board-action-row-double">
                      <input
                        onChange={(event) => setTwoSplitLeftColor(event.target.value)}
                        type="color"
                        value={twoSplitLeftColor}
                      />
                      <input
                        onChange={(event) => setTwoSplitRightColor(event.target.value)}
                        type="color"
                        value={twoSplitRightColor}
                      />
                      <button
                        disabled={!lightingModel}
                        onClick={() =>
                          lightingModel &&
                          handleBoardPreset(
                            applyTwoColorSplit(
                              lightingModel.keys,
                              twoSplitLeftColor,
                              twoSplitRightColor,
                            ),
                          )
                        }
                        type="button"
                      >
                        Split
                      </button>
                    </div>
                  </div>

                  <div className="board-action-group">
                    <span className="meta-label">Three-Color Split</span>
                    <div className="board-action-row board-action-row-triple">
                      <input
                        onChange={(event) => setThreeSplitLeftColor(event.target.value)}
                        type="color"
                        value={threeSplitLeftColor}
                      />
                      <input
                        onChange={(event) => setThreeSplitCenterColor(event.target.value)}
                        type="color"
                        value={threeSplitCenterColor}
                      />
                      <input
                        onChange={(event) => setThreeSplitRightColor(event.target.value)}
                        type="color"
                        value={threeSplitRightColor}
                      />
                      <button
                        disabled={!lightingModel}
                        onClick={() =>
                          lightingModel &&
                          handleBoardPreset(
                            applyThreeColorSplit(
                              lightingModel.keys,
                              threeSplitLeftColor,
                              threeSplitCenterColor,
                              threeSplitRightColor,
                            ),
                          )
                        }
                        type="button"
                      >
                        Split
                      </button>
                    </div>
                  </div>

                  <div className="board-action-group">
                    <span className="meta-label">Checker</span>
                    <div className="board-action-row board-action-row-double">
                      <input
                        onChange={(event) => setCheckerPrimaryColor(event.target.value)}
                        type="color"
                        value={checkerPrimaryColor}
                      />
                      <input
                        onChange={(event) => setCheckerSecondaryColor(event.target.value)}
                        type="color"
                        value={checkerSecondaryColor}
                      />
                      <button
                        disabled={!lightingModel}
                        onClick={() =>
                          lightingModel &&
                          handleBoardPreset(
                            applyCheckerPattern(
                              lightingModel.keys,
                              checkerPrimaryColor,
                              checkerSecondaryColor,
                            ),
                          )
                        }
                        type="button"
                      >
                        Checker
                      </button>
                    </div>
                  </div>

                  <div className="board-action-group">
                    <span className="meta-label">Rainbow</span>
                    <div className="board-action-row">
                      <button
                        disabled={!lightingModel}
                        onClick={() =>
                          lightingModel && handleBoardPreset(applyRainbowPreset(lightingModel.keys))
                        }
                        type="button"
                      >
                        Apply rainbow
                      </button>
                    </div>
                  </div>
                </section>
                </section>
              </>
            ) : activeScreen === "Keymap" ? (
              <>
                <section className="panel inspector-panel">
                  <div className="panel-header compact-header">
                    <div>
                      <p className="panel-kicker">Selected Key</p>
                      <h2>{workspaceContent.inspectorTitle}</h2>
                    </div>
                    <span className="selection-pill subtle-pill">Base + FN</span>
                  </div>

                  <div className="lighting-meta-row">
                    <span>{keymapModel?.verificationStatus ?? (keymapLoading ? "Loading" : "Unavailable")}</span>
                    <span>{`${keymapAssignments.length} mapped keys`}</span>
                    <span>
                      {stagedKeymapEditCount === 0 ? "Ready to edit" : "Staged changes pending"}
                    </span>
                  </div>

                  {selectedKeymapAssignment ? (
                    <>
                      <div className="inspector-key">
                        <div className="preview-keycap keymap-preview-keycap">
                          {selectedKeymapAssignment.label}
                        </div>
                        <div>
                          <strong>{selectedKeymapAssignment.label}</strong>
                          <p>{selectedKeymapAssignment.logicalId}</p>
                        </div>
                      </div>

                      <div className="keymap-controls">
                        <label className="select-control">
                          <span className="meta-label">Base action</span>
                          <DropdownSelect
                            ariaLabel={`Set base action for ${selectedKeymapAssignment.label}`}
                            onChange={(value) =>
                              handleKeymapActionChange(
                                selectedKeymapAssignment.uiKey,
                                "base_raw_value",
                                Number(value),
                              )
                            }
                            options={keymapDropdownOptions}
                            value={String(selectedKeymapBaseRawValue ?? 0)}
                          />
                        </label>

                        <label className="select-control">
                          <span className="meta-label">FN action</span>
                          <DropdownSelect
                            ariaLabel={`Set FN action for ${selectedKeymapAssignment.label}`}
                            onChange={(value) =>
                              handleKeymapActionChange(
                                selectedKeymapAssignment.uiKey,
                                "fn_raw_value",
                                Number(value),
                              )
                            }
                            options={keymapDropdownOptions}
                            value={String(selectedKeymapFnRawValue ?? 0)}
                          />
                        </label>
                      </div>
                    </>
                  ) : (
                    <div className="lighting-empty-state lighting-empty-panel">
                      <strong>Select a key</strong>
                      <p>Choose a key on the board to edit its base and FN-layer assignments.</p>
                    </div>
                  )}

                  <div className="inspector-actions">
                    <button
                      disabled={stagedKeymapEditCount === 0 || keymapApplying}
                      onClick={() => void handleApplyKeymap()}
                      type="button"
                    >
                      {keymapApplying ? "Applying..." : "Apply staged edits"}
                    </button>
                    <button
                      className="secondary-button"
                      disabled={stagedKeymapEditCount === 0}
                      onClick={() => void handleResetKeymap()}
                      type="button"
                    >
                      Reset
                    </button>
                  </div>
                </section>

                <section className="panel board-actions-panel">
                  <div className="panel-header compact-header board-actions-header">
                    <div>
                      <p className="panel-kicker">Selected Assignment</p>
                      <h2>Current mapping</h2>
                    </div>
                  </div>

                  {selectedKeymapAssignment ? (
                    <div className="summary-grid">
                      <div>
                        <span className="meta-label">Base</span>
                        <strong>{selectedKeymapAssignment.baseAction.label}</strong>
                      </div>
                      <div>
                        <span className="meta-label">FN</span>
                        <strong>{selectedKeymapAssignment.fnAction.label}</strong>
                      </div>
                      <div>
                        <span className="meta-label">Protocol Position</span>
                        <strong>{selectedKeymapAssignment.protocolPos}</strong>
                      </div>
                      <div>
                        <span className="meta-label">Logical Id</span>
                        <strong>{selectedKeymapAssignment.logicalId}</strong>
                      </div>
                    </div>
                  ) : (
                    <div className="lighting-empty-state lighting-empty-panel">
                      <strong>No key selected</strong>
                      <p>The right-side editor will populate after you select a key on the board.</p>
                    </div>
                  )}
                </section>
              </>
            ) : activeScreen === "Macros" ? (
              <>
                <section className="panel inspector-panel">
                  <div className="panel-header compact-header">
                    <div>
                      <p className="panel-kicker">Macro Editor</p>
                      <h2>{workspaceContent.inspectorTitle}</h2>
                    </div>
                    <span className="selection-pill subtle-pill">
                      {macrosModel?.supported ? "Wired macros" : "Unavailable"}
                    </span>
                  </div>

                  {macrosError ? <p className="profile-error">{macrosError}</p> : null}

                  {!macrosModel?.supported ? (
                    <div className="lighting-empty-state lighting-empty-panel">
                      <strong>Macros unavailable</strong>
                      <p>{macrosModel?.reason ?? "Macros require wired USB mode on this keyboard."}</p>
                    </div>
                  ) : (
                    <>
                      <div className="profiles-toolbar macros-toolbar">
                        <label className="select-control">
                          <span className="meta-label">Macro slot</span>
                          <DropdownSelect
                            ariaLabel="Select macro slot"
                            onChange={(value) =>
                              setSelectedMacroSlotId(value === "new" ? null : Number(value))
                            }
                            options={macroSlotDropdownOptions}
                            value={selectedMacroSlotId === null ? "new" : String(selectedMacroSlotId)}
                          />
                        </label>
                        <button
                          className="secondary-button"
                          onClick={handleCreateNewMacroDraft}
                          type="button"
                        >
                          New Macro
                        </button>
                      </div>

                      <div className="summary-grid">
                        <div>
                          <span className="meta-label">Bound key</span>
                          <strong>
                            {macroDraftBoundUiKey
                              ? keyboardAsset?.keysByUiKey.get(macroDraftBoundUiKey)?.label ?? macroDraftBoundUiKey
                              : "Click keyboard to bind"}
                          </strong>
                        </div>
                        <div>
                          <span className="meta-label">Execution</span>
                          <strong>{macroDraftExecutionType}</strong>
                        </div>
                        <div>
                          <span className="meta-label">Actions</span>
                          <strong>{macroDraftActions.length}</strong>
                        </div>
                      </div>

                      <div className="keymap-controls">
                        <label className="hex-control">
                          <span className="meta-label">Name</span>
                          <input
                            onChange={(event) => setMacroDraftName(event.target.value)}
                            type="text"
                            value={macroDraftName}
                          />
                        </label>

                        <label className="select-control">
                          <span className="meta-label">Execution type</span>
                          <DropdownSelect
                            ariaLabel="Select macro execution type"
                            onChange={setMacroDraftExecutionType}
                            options={macroExecutionOptions}
                            value={macroDraftExecutionType}
                          />
                        </label>

                        <label className="hex-control">
                          <span className="meta-label">Cycle count</span>
                          <input
                            disabled={macroDraftExecutionType !== "FIXED_COUNT"}
                            min="1"
                            onChange={(event) => setMacroDraftCycleTimes(event.target.value)}
                            type="number"
                            value={macroDraftCycleTimes}
                          />
                        </label>
                      </div>

                      <div className="macro-actions-list">
                        {macroDraftActions.length > 0 ? (
                          macroDraftActions.map((action, index) => (
                            <div className="macro-action-row" key={`${action.key}-${index}`}>
                              <label className="select-control">
                                <span className="meta-label">Key</span>
                                <DropdownSelect
                                  ariaLabel={`Select macro key ${index + 1}`}
                                  onChange={(value) => handleMacroActionChange(index, "key", value)}
                                  options={macroKeyDropdownOptions}
                                  value={action.key}
                                />
                              </label>
                              <label className="select-control">
                                <span className="meta-label">Event</span>
                                <DropdownSelect
                                  ariaLabel={`Select macro event ${index + 1}`}
                                  onChange={(value) =>
                                    handleMacroActionChange(index, "eventType", value)
                                  }
                                  options={macroEventOptions}
                                  value={action.eventType}
                                />
                              </label>
                              <label className="hex-control">
                                <span className="meta-label">Delay ms</span>
                                <input
                                  min="0"
                                  onChange={(event) =>
                                    handleMacroActionChange(
                                      index,
                                      "delayMs",
                                      Number(event.target.value),
                                    )
                                  }
                                  type="number"
                                  value={String(action.delayMs)}
                                />
                              </label>
                              <button
                                className="secondary-button"
                                onClick={() => handleRemoveMacroAction(index)}
                                type="button"
                              >
                                Remove
                              </button>
                            </div>
                          ))
                        ) : (
                          <div className="lighting-empty-state lighting-empty-panel">
                            <strong>No macro actions yet</strong>
                            <p>Add key events, then click the keyboard image to bind the macro.</p>
                          </div>
                        )}
                      </div>

                      <div className="inspector-actions">
                        <button onClick={handleAddMacroAction} type="button">
                          Add Action
                        </button>
                        <button
                          disabled={macrosApplying}
                          onClick={() => void handleSaveMacro()}
                          type="button"
                        >
                          {macrosApplying ? "Saving..." : "Save Macro"}
                        </button>
                        <button
                          className="secondary-button"
                          disabled={selectedMacroSlotId === null || macrosDeleting}
                          onClick={() => void handleDeleteMacro()}
                          type="button"
                        >
                          {macrosDeleting ? "Deleting..." : "Delete Macro"}
                        </button>
                      </div>
                    </>
                  )}
                </section>

                <section className="panel board-actions-panel">
                  <div className="panel-header compact-header board-actions-header">
                    <div>
                      <p className="panel-kicker">Bindings</p>
                      <h2>Current macro slots</h2>
                    </div>
                  </div>

                  {macrosModel?.slots.length ? (
                    <div className="profiles-list macro-slots-list">
                      {macrosModel.slots.map((slot) => (
                        <button
                          className={`profile-card ${selectedMacroSlotId === slot.slotId ? "profile-card-active" : ""}`}
                          key={slot.slotId}
                          onClick={() => setSelectedMacroSlotId(slot.slotId)}
                          type="button"
                        >
                          <div className="profile-card-header">
                            <strong>{slot.name}</strong>
                            <span className="selection-pill subtle-pill">{`Slot ${slot.slotId + 1}`}</span>
                          </div>
                          <div className="profile-card-meta">
                            <span>{slot.executionType}</span>
                            <span>{`${slot.actions.length} actions`}</span>
                            <span>
                              {slot.boundUiKeys.length > 0
                                ? slot.boundUiKeys
                                    .map(
                                      (uiKey) =>
                                        keyboardAsset?.keysByUiKey.get(uiKey)?.label ?? uiKey,
                                    )
                                    .join(", ")
                                : "Unbound"}
                            </span>
                          </div>
                        </button>
                      ))}
                    </div>
                  ) : (
                    <div className="lighting-empty-state lighting-empty-panel">
                      <strong>No macros saved</strong>
                      <p>Create a macro, add actions, then click the keyboard to bind it.</p>
                    </div>
                  )}
                </section>
              </>
            ) : activeScreen === "Device" ? (
              <section className="panel device-capabilities-panel">
                <div className="panel-header compact-header">
                  <div>
                    <p className="panel-kicker">Capabilities</p>
                    <h2>Feature Surface</h2>
                  </div>
                </div>

                <div className="summary-grid">
                  <div>
                    <span className="meta-label">Per-key RGB</span>
                    <strong>{lightingModel?.perKeyRgbSupported ? "Available" : "Unknown"}</strong>
                  </div>
                  <div>
                    <span className="meta-label">Profiles</span>
                    <strong>
                      {effectiveDashboard.device.supportsProfiles ? "Supported" : "Unsupported"}
                    </strong>
                  </div>
                  <div>
                    <span className="meta-label">Lighting Mode</span>
                    <strong>{lightingModel?.mode ?? "Unknown"}</strong>
                  </div>
                  <div>
                    <span className="meta-label">Brightness</span>
                    <strong>{lightingModel ? `${lightingModel.brightness}%` : "Unknown"}</strong>
                  </div>
                  <div>
                    <span className="meta-label">Last Sync</span>
                    <strong>{lastSync}</strong>
                  </div>
                </div>
              </section>
            ) : activeScreen === "Profiles" ? (
              <section className="panel inspector-panel">
                <div className="panel-header compact-header">
                  <div>
                    <p className="panel-kicker">Profiles</p>
                    <h2>{workspaceContent.inspectorTitle}</h2>
                  </div>
                  <span className="selection-pill subtle-pill">
                    {effectiveDashboard.device.supportsProfiles ? "Available" : "Unsupported"}
                  </span>
                </div>

                {selectedSavedProfile ? (
                  <>
                    <div className="summary-grid">
                      <div>
                        <span className="meta-label">Lighting Mode</span>
                        <strong>{selectedSavedProfile.lighting.mode}</strong>
                      </div>
                      <div>
                        <span className="meta-label">Brightness</span>
                        <strong>{selectedSavedProfile.lighting.brightness}%</strong>
                      </div>
                      <div>
                        <span className="meta-label">Lit Keys</span>
                        <strong>{Object.keys(selectedSavedProfile.lighting.keys).length}</strong>
                      </div>
                      <div>
                        <span className="meta-label">Mapped Keys</span>
                        <strong>{Object.keys(selectedSavedProfile.keymap.assignments).length}</strong>
                      </div>
                    </div>
                    <div className="summary-foot">
                      <div className="signal-block compact-signal">
                        <span className="meta-label">Updated</span>
                        <strong>{new Date(selectedSavedProfile.updatedAt).toLocaleString()}</strong>
                      </div>
                    </div>
                    <div className="inspector-actions">
                      <button
                        disabled={profilesApplyingId === selectedSavedProfile.snapshotId}
                        onClick={() => void handleApplyProfile(selectedSavedProfile.snapshotId)}
                        type="button"
                      >
                        {profilesApplyingId === selectedSavedProfile.snapshotId ? "Applying..." : "Apply to keyboard"}
                      </button>
                    </div>
                  </>
                ) : (
                  <div className="lighting-empty-state lighting-empty-panel">
                    <strong>No profile selected</strong>
                    <p>Choose a saved profile to inspect it and apply it back to the keyboard.</p>
                  </div>
                )}
              </section>
            ) : activeScreen === "Events" ? (
              <section className="panel events-summary-panel">
                <div className="panel-header compact-header">
                  <div>
                    <p className="panel-kicker">Summary</p>
                    <h2>Event Totals</h2>
                  </div>
                </div>

                <div className="summary-grid">
                  <div>
                    <span className="meta-label">Read</span>
                    <strong>{eventCounts.read}</strong>
                  </div>
                  <div>
                    <span className="meta-label">Write</span>
                    <strong>{eventCounts.write}</strong>
                  </div>
                  <div>
                    <span className="meta-label">Meta</span>
                    <strong>{eventCounts.meta}</strong>
                  </div>
                  <div>
                    <span className="meta-label">Last Sync</span>
                    <strong>{lastSync}</strong>
                  </div>
                </div>
              </section>
            ) : (
              <section className="panel inspector-panel">
                <div className="panel-header compact-header">
                  <div>
                    <p className="panel-kicker">Inspector</p>
                    <h2>{workspaceContent.inspectorTitle}</h2>
                  </div>
                  <span className="selection-pill subtle-pill">Editor</span>
                </div>

                <div className="lighting-empty-state lighting-empty-panel">
                  <strong>{workspaceContent.inspectorTitle}</strong>
                  <p>This page keeps its own editor surface. Hardware details and recent traffic no longer live here.</p>
                </div>
              </section>
            )}
          </aside>
        </div>
      </section>
    </main>
  );
}

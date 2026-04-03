import { startTransition, useDeferredValue, useEffect, useState } from "react";

import { DeviceCard } from "./components/device-card";
import { TracePanel } from "./components/trace-panel";
import {
  applyPerKeyLighting,
  loadDashboardModel,
  loadPerKeyLightingModel,
  type DashboardModel,
  type PerKeyLightingModel,
} from "./lib/api";
import { buildRenderedLightingState } from "./lib/lighting";
import {
  applyCheckerPattern,
  applyRainbowPreset,
  applySolidFill,
  applyThreeColorSplit,
  applyTwoColorSplit,
  physicalKeyboardBlocks,
  physicalKeyboardLayout,
  type PhysicalBoardItem,
} from "./lib/lighting-layout";
import { defaultScreen, primaryNavigation, type PrimaryScreen } from "./lib/navigation";
import { buildHeaderChips, shouldShowDeviceCard } from "./lib/screen-chrome";
import { buildWorkspaceContent } from "./lib/workspace";

const initialDashboard: DashboardModel = {
  device: {
    activeProfile: "Scanning...",
    connected: false,
    dirty: false,
    firmware: "Waiting for API",
    interfaceName: "Vendor HID handshake pending",
    protocol: "bytech",
    status: "disconnected",
    supportedDevices: ["Kreo Swarm"],
    syncState: "Bootstrapping",
    targetName: "Kreo Swarm",
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

function buildKeyClasses(
  item: PhysicalBoardItem,
  isSelectable: boolean,
  isSelected: boolean,
  shouldDim: boolean,
): string {
  const classNames = ["board-key"];

  if (item.kind === "spacer") {
    classNames.push("board-spacer");
  }
  if (item.kind === "knob") {
    classNames.push("board-knob");
  }
  classNames.push(`board-key-${item.width}`);
  if (item.section) {
    classNames.push(`board-key-${item.section}`);
  }
  if (shouldDim) {
    classNames.push("board-key-dimmed");
  }
  if (isSelectable) {
    classNames.push("board-key-selectable");
  }
  if (isSelected) {
    classNames.push("board-key-selected");
  }

  return classNames.join(" ");
}

export function App() {
  const [dashboard, setDashboard] = useState<DashboardModel>(initialDashboard);
  const [activeScreen, setActiveScreen] = useState<PrimaryScreen>(defaultScreen);
  const [lastSync, setLastSync] = useState("Connecting to loopback API");
  const [lightingModel, setLightingModel] = useState<PerKeyLightingModel | null>(null);
  const [lightingError, setLightingError] = useState<string | null>(null);
  const [lightingLoading, setLightingLoading] = useState(false);
  const [lightingApplying, setLightingApplying] = useState(false);
  const [selectedLightingKeyId, setSelectedLightingKeyId] = useState<string | null>(null);
  const [stagedLightingEdits, setStagedLightingEdits] = useState<Record<string, string>>({});
  const [lightingColorInput, setLightingColorInput] = useState("#273240");
  const [solidFillColor, setSolidFillColor] = useState("#00ffaa");
  const [twoSplitLeftColor, setTwoSplitLeftColor] = useState("#ff4d4d");
  const [twoSplitRightColor, setTwoSplitRightColor] = useState("#356dff");
  const [threeSplitLeftColor, setThreeSplitLeftColor] = useState("#ff4d4d");
  const [threeSplitCenterColor, setThreeSplitCenterColor] = useState("#00ffaa");
  const [threeSplitRightColor, setThreeSplitRightColor] = useState("#356dff");
  const [checkerPrimaryColor, setCheckerPrimaryColor] = useState("#ff4d4d");
  const [checkerSecondaryColor, setCheckerSecondaryColor] = useState("#356dff");
  const deferredTraceEntries = useDeferredValue(dashboard.traceEntries);
  const workspaceContent = buildWorkspaceContent(activeScreen);
  const isLightingScreen = activeScreen === "Lighting";
  const stagedEditCount = Object.keys(stagedLightingEdits).length;

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
    let cancelled = false;

    async function hydrateDashboard() {
      const model = await loadDashboardModel();
      if (cancelled) {
        return;
      }

      startTransition(() => {
        setDashboard(model);
        setLastSync(
          new Intl.DateTimeFormat(undefined, {
            hour: "2-digit",
            minute: "2-digit",
            second: "2-digit",
          }).format(new Date()),
        );
      });
    }

    void hydrateDashboard();

    return () => {
      cancelled = true;
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
    if (!isLightingScreen || stagedEditCount > 0) {
      return;
    }

    const intervalId = window.setInterval(() => {
      void hydrateLightingState();
    }, 3000);

    return () => window.clearInterval(intervalId);
  }, [isLightingScreen, stagedEditCount]);

  const renderedLightingKeys =
    isLightingScreen && lightingModel
      ? buildRenderedLightingState(lightingModel.keys, stagedLightingEdits)
      : [];
  const lightingKeyMap = new Map(renderedLightingKeys.map((entry) => [entry.uiKey, entry]));
  const selectedLightingKey = selectedLightingKeyId
    ? lightingKeyMap.get(selectedLightingKeyId) ?? null
    : null;
  const selectedLightingLayoutItem = selectedLightingKeyId
    ? physicalKeyboardLayout.find((item) => item.id === selectedLightingKeyId) ?? null
    : null;
  const selectedLightingDisplayLabel =
    selectedLightingLayoutItem?.label ?? selectedLightingKey?.label ?? "Key";

  useEffect(() => {
    if (selectedLightingKey) {
      setLightingColorInput(selectedLightingKey.color);
    }
  }, [selectedLightingKey]);

  const effectiveDashboard: DashboardModel = {
    ...dashboard,
    device: {
      ...dashboard.device,
      dirty: dashboard.device.dirty || stagedEditCount > 0,
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
    setSelectedLightingKeyId(keyId);
  }

  function handleLightingColorChange(nextColor: string) {
    if (!selectedLightingKey) {
      return;
    }

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
    setStagedLightingEdits(edits);
  }

  async function handleApplyLighting() {
    if (stagedEditCount === 0) {
      return;
    }

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
    setStagedLightingEdits({});
    await hydrateLightingState();
  }

  function renderBoardItem(item: PhysicalBoardItem) {
    const lightingEntry = lightingKeyMap.get(item.id);
    const isSelectable = isLightingScreen && item.editable && lightingEntry !== undefined;
    const isSelected = selectedLightingKeyId === item.id;
    const shouldDim = !item.editable || (isLightingScreen && lightingEntry === undefined);
    const className = buildKeyClasses(item, isSelectable, isSelected, shouldDim);

    if (item.kind === "spacer") {
      return <div aria-hidden="true" className={className} key={item.id} />;
    }

    if (item.kind === "knob") {
      return (
        <div className={className} key={item.id}>
          <div className="knob-core" />
        </div>
      );
    }

    const style =
      isSelectable && lightingEntry
        ? {
            backgroundColor: lightingEntry.color,
            color: getKeyTextColor(lightingEntry.color),
          }
        : undefined;

    return (
      <button
        className={className}
        disabled={!isSelectable}
        key={item.id}
        onClick={() => handleSelectLightingKey(item.id)}
        style={style}
        type="button"
      >
        {item.label}
      </button>
    );
  }

  const refreshStateLabel =
    stagedEditCount === 0 ? "Auto-refresh live" : "Refresh paused while dirty";
  const pageGridClass =
    activeScreen === "Lighting"
      ? "page-grid lighting-grid"
      : activeScreen === "Device"
        ? "page-grid device-grid"
        : activeScreen === "Events"
          ? "page-grid events-grid"
          : "page-grid standard-grid";

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
            {headerChips.map((chip, index) =>
              isLightingScreen && index === 1 ? (
                <span
                  className={`status-pill status-${effectiveDashboard.device.status}`}
                  key={`${chip}-${index}`}
                >
                  {chip}
                </span>
              ) : (
                <span className="header-chip" key={`${chip}-${index}`}>
                  {chip}
                </span>
              ),
            )}
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
                  {lightingError ? (
                    <div className="lighting-empty-state">
                      <strong>Lighting session unavailable</strong>
                      <p>{lightingError}</p>
                    </div>
                  ) : (
                    <div className="board-shell">
                      {physicalKeyboardBlocks.map((block) => (
                        <section
                          className={`board-block board-block-${block.id}`}
                          key={block.id}
                        >
                          {block.rows.map((row, rowIndex) => (
                            <div className="board-row" key={`${block.id}-${rowIndex}`}>
                              {row.map((item) => renderBoardItem(item))}
                            </div>
                          ))}
                        </section>
                      ))}
                    </div>
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

import { renderStatus } from "../lib/status";
import type { DeviceSummary } from "../lib/api";

interface DeviceCardProps {
  device: DeviceSummary;
}

export function DeviceCard({ device }: DeviceCardProps) {
  return (
    <article className="panel device-summary-card">
      <div className="panel-header compact-header">
        <div>
          <p className="panel-kicker">Device</p>
          <h2>{device.targetName}</h2>
        </div>
        <span className={`status-pill status-${device.status}`}>
          {renderStatus(device.status)}
        </span>
      </div>

      <div className="summary-grid">
        <div>
          <span className="meta-label">Active Profile</span>
          <strong>{device.activeProfile}</strong>
        </div>
        <div>
          <span className="meta-label">Sync</span>
          <strong>{device.syncState}</strong>
        </div>
        <div>
          <span className="meta-label">Protocol</span>
          <strong>{device.protocol}</strong>
        </div>
        <div>
          <span className="meta-label">Interface</span>
          <strong>{device.interfaceName}</strong>
        </div>
      </div>

      <div className="summary-foot">
        <div className={`signal-block compact-signal ${device.dirty ? "signal-warn" : "signal-ok"}`}>
          <span className="meta-label">Dirty State</span>
          <strong>{device.dirty ? "Pending changes" : "Synced"}</strong>
        </div>
        <div className="signal-block compact-signal">
          <span className="meta-label">Firmware</span>
          <strong>{device.firmware}</strong>
        </div>
      </div>
    </article>
  );
}

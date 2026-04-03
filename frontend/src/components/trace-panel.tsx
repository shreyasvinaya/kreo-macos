import type { TraceEntry } from "../lib/api";

interface TracePanelProps {
  entries: TraceEntry[];
}

export function TracePanel({ entries }: TracePanelProps) {
  return (
    <article className="panel trace-panel quiet-panel">
      <div className="panel-header compact-header">
        <div>
          <p className="panel-kicker">Activity</p>
          <h2>Recent Device Events</h2>
        </div>
        <span className="trace-count">{entries.length} events</span>
      </div>

      <div className="trace-list">
        {entries.map((entry) => (
          <div className="trace-entry" key={`${entry.timestamp}-${entry.label}`}>
            <div className="trace-head">
              <span className={`trace-direction trace-${entry.direction}`}>
                {entry.direction}
              </span>
              <strong>{entry.label}</strong>
            </div>
            <div className="trace-payload">
              <span>report {entry.reportId}</span>
              <code>{entry.payloadHex}</code>
            </div>
            <time>{entry.timestamp}</time>
          </div>
        ))}
      </div>
    </article>
  );
}

export type ConnectionStatus = "connected" | "disconnected";

export function renderStatus(status: ConnectionStatus): string {
  return status === "connected" ? "Connected" : "Disconnected";
}


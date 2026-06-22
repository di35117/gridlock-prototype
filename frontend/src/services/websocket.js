// src/services/websocket.js
import { useSystemStore } from "../store/useSystemStore";

// Pulls from Vercel in production, or defaults to localhost in development
const API_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

// DEFENSIVE FIX: If the protocol is missing from the env variable, patch it manually
let absoluteApiUrl = API_URL;
if (
  !absoluteApiUrl.startsWith("http://") &&
  !absoluteApiUrl.startsWith("https://")
) {
  absoluteApiUrl =
    absoluteApiUrl.includes("localhost") || absoluteApiUrl.includes("127.0.0.1")
      ? `http://${absoluteApiUrl}`
      : `https://${absoluteApiUrl}`;
}

// Magically swaps https:// for wss:// and http:// for ws://
const WS_URL =
  absoluteApiUrl.replace("https://", "wss://").replace("http://", "ws://") +
  "/api/stream/live";

let ws = null;

export const connectSystemWebSocket = () => {
  if (ws) return;

  ws = new WebSocket(WS_URL);

  ws.onmessage = async (event) => {
    const data = JSON.parse(event.data);
    const store = useSystemStore.getState();

    // 1. Send all telemetry to the Intel Feed component
    store.addIntelAlert(data);

    // 2. Evaluate if event critical criteria triggers Copilot actions
    if (
      data.type === "TRAFFIC_SURGE" ||
      data.type === "CRITICAL_ALERT" ||
      data.type === "CCTV_ANOMALY"
    ) {
      if (
        data.ui_action === "TRIGGER_SIREN_AND_SNAP_MAP" ||
        data.type === "TRAFFIC_SURGE"
      ) {
        store.triggerSurgeResponse(data.payload || data);

        try {
          const API_BASE =
            import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";
          const res = await fetch(`${API_BASE}/api/copilot/execute`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ event_id: data.id || data.event_id }),
          });
          const executionData = await res.json();

          let pollInterval = setInterval(async () => {
            try {
              const statusRes = await fetch(
                `${API_BASE}/api/copilot/status/${executionData.task_id}`,
              );
              const statusData = await statusRes.json();

              if (statusData.status === "completed") {
                clearInterval(pollInterval);

                let finalBarricades = [];
                if (statusData.barricades) {
                  finalBarricades = Object.values(statusData.barricades);
                }

                store.resolveSurgeResponse(
                  statusData.operational_order,
                  finalBarricades,
                  statusData.diversion_routes || null,
                  statusData.resources || null,
                  statusData.compound_threats || null,
                );
              } else if (statusData.status === "failed") {
                clearInterval(pollInterval);
                store.resolveSurgeResponse(
                  "Tactical operational plan creation failed.",
                  [],
                  null,
                  null,
                );
              }
            } catch (pollErr) {
              console.error(
                "Asynchronous execution status poll error encountered:",
                pollErr,
              );
              clearInterval(pollInterval);
            }
          }, 2000);
        } catch (error) {
          console.error("Automated Copilot execution failed:", error);
          store.resolveSurgeResponse(
            "Failed to connect to AI Copilot service.",
            [],
            null,
            null,
          );
        }
      }
    }
  };

  ws.onclose = () => {
    ws = null;
    setTimeout(connectSystemWebSocket, 3000); // Trigger auto-reconnect fallback loop
  };
};

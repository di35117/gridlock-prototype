// src/services/websocket.js
import { useSystemStore } from "../store/useSystemStore";

const IS_PROD = import.meta.env.MODE === "production";
const WS_URL = IS_PROD
  ? "wss://gridlock-prototype-production.up.railway.app/api/stream/live"
  : "ws://localhost:8000/api/stream/live";
const API_URL = IS_PROD
  ? "https://gridlock-prototype-production.up.railway.app"
  : "http://localhost:8000";

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
          // Extract coordinate items cleanly from live event stream payload structures
          const eventLat = data.payload?.latitude || data.latitude || 12.9716;
          const eventLon = data.payload?.longitude || data.longitude || 77.5946;

          // Dispatch generation request containing accurate telemetry data coordinates
          const initialResponse = await fetch(
            `${API_URL}/api/copilot/generate`,
            {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({
                event_cause: data.type,
                corridor:
                  data.corridor || (data.payload ? data.payload.corridor : ""),
                expected_crowd: data.payload?.expected_crowd || 1000,
                event_details: data.message || data.payload?.message || "",
                event_datetime: new Date().toISOString(),
                latitude: parseFloat(eventLat),
                longitude: parseFloat(eventLon),
              }),
            },
          );

          const initialData = await initialResponse.json();
          const task_id = initialData.task_id;

          if (!task_id) {
            console.error(
              "Failed to acquire tracking task identifier from Copilot engine backend.",
            );
            return;
          }

          // Initialize state check interval polling loop
          const pollInterval = setInterval(async () => {
            try {
              const statusResponse = await fetch(
                `${API_URL}/api/copilot/status/${task_id}`,
              );
              const statusData = await statusResponse.json();

              if (statusData.status === "completed") {
                clearInterval(pollInterval);

                // Read barricades list or establish clear algorithmic boundaries around localized threat
                let finalBarricades = statusData.barricades || [];
                if (finalBarricades.length === 0 && store.activeSurge) {
                  const lat = store.activeSurge.latitude || 12.9716;
                  const lon = store.activeSurge.longitude || 77.5946;
                  finalBarricades = [
                    [lon + 0.002, lat + 0.002],
                    [lon - 0.002, lat - 0.002],
                    [lon + 0.002, lat - 0.002],
                  ];
                }

                // Push completed state payloads directly into state storage hooks
                store.resolveSurgeResponse(
                  statusData.operational_order,
                  finalBarricades,
                  statusData.diversion_routes || null,
                  statusData.resources || null, // Feeds the Resource Dashboard
                  statusData.compound_threats || null, // Feeds the Conflict Radar
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


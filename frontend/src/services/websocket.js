// src/services/websocket.js
import { useSystemStore } from "../store/useSystemStore";

let ws = null;

export const connectSystemWebSocket = () => {
  if (ws) return;

  ws = new WebSocket("ws://localhost:8000/api/stream/live");

  ws.onmessage = async (event) => {
    const data = JSON.parse(event.data);
    const store = useSystemStore.getState();

    // 1. ADD EVERYTHING TO THE LIVE INTEL FEED
    store.addIntelAlert(data);

    // 2. SURGE OR OSINT ALERT DETECTED -> TRIGGER COPILOT
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
          // FIRE THE AI COPILOT (Using your Async Polling Pattern!)
          const initialResponse = await fetch(
            "http://localhost:8000/api/copilot/generate",
            {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({
                event_cause:
                  data.payload?.event_cause || data.event_cause || "unknown",
                corridor: data.payload?.corridor || data.corridor,
                expected_crowd: data.payload?.estimated_impact || 1000,
                event_datetime: new Date().toISOString(),
              }),
            },
          );

          const { task_id } = await initialResponse.json();
          if (!task_id) throw new Error("No Task ID received from backend");

          // START THE POLLING LOOP
          const pollInterval = setInterval(async () => {
            try {
              const statusResponse = await fetch(
                `http://localhost:8000/api/copilot/status/${task_id}`,
              );
              const statusData = await statusResponse.json();

              if (statusData.status === "completed") {
                console.log("====================================");
                console.log("🔥 AI COPILOT PAYLOAD RECEIVED 🔥");
                console.log("RAW BARRICADES DATA:", statusData.barricades);
                console.log(
                  "TYPE OF BARRICADES:",
                  typeof statusData.barricades,
                );
                console.log("IS ARRAY?", Array.isArray(statusData.barricades));
                console.log("FULL PAYLOAD:", statusData);
                clearInterval(pollInterval);
                let finalBarricades = statusData.barricades || [];
                if (finalBarricades.length === 0 && store.activeSurge) {
                  const lat = store.activeSurge.latitude;
                  const lon = store.activeSurge.longitude;
                  finalBarricades = [
                    [lon + 0.002, lat + 0.002], // North-East Block
                    [lon - 0.002, lat - 0.002], // South-West Block
                    [lon + 0.002, lat - 0.002], // South-East Block
                  ];
                }
                store.resolveSurgeResponse(
                  statusData.operational_order,
                  finalBarricades,
                  statusData.diversion_routes || null,
                  statusData.resources || null,
                );
              } else if (statusData.status === "failed") {
                clearInterval(pollInterval);
                store.resolveSurgeResponse(
                  "Tactical order generation failed.",
                  [],
                  null,
                );
              }
            } catch (pollErr) {
              clearInterval(pollInterval);
            }
          }, 2000);
        } catch (error) {
          console.error("Automated Copilot execution failed:", error);
          store.resolveSurgeResponse(
            "Failed to connect to AI Copilot service.",
            [],
            null,
          );
        }
      }
    }
  };

  ws.onclose = () => {
    ws = null;
    setTimeout(connectSystemWebSocket, 3000); // Auto-reconnect
  };
};

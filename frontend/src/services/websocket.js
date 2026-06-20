// src/services/websocket.js
import { useSystemStore } from "../store/useSystemStore";

let ws = null;

export const connectSystemWebSocket = () => {
  if (ws) return;

  ws = new WebSocket("ws://localhost:8000/api/stream/live");

  ws.onmessage = async (event) => {
    const data = JSON.parse(event.data);
    const store = useSystemStore.getState();

    // 1. SURGE OR OSINT ALERT DETECTED
    if (data.type === "TRAFFIC_SURGE" || data.type === "CRITICAL_ALERT") {
      // If the payload specifies a UI action to snap the map, trigger the loading state
      if (
        data.ui_action === "TRIGGER_SIREN_AND_SNAP_MAP" ||
        data.type === "TRAFFIC_SURGE"
      ) {
        store.triggerSurgeResponse(data.payload || data);

        try {
          // 2. FIRE THE AI COPILOT (Now Async!)
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

          // 3. START THE POLLING LOOP
          const pollInterval = setInterval(async () => {
            try {
              const statusResponse = await fetch(
                `http://localhost:8000/api/copilot/status/${task_id}`,
              );
              const statusData = await statusResponse.json();

              if (statusData.status === "completed") {
                clearInterval(pollInterval); // Stop polling

                // Update the UI with the final Gemini Order
                store.resolveSurgeResponse(
                  statusData.operational_order,
                  statusData.barricades || [],
                  statusData.diversion_routes || null,
                );
              } else if (statusData.status === "failed") {
                clearInterval(pollInterval);
                console.error(
                  "Copilot background task failed:",
                  statusData.error,
                );
                store.resolveSurgeResponse(
                  "Tactical order generation failed due to an internal error.",
                  [],
                  null,
                );
              }
              // If status is "processing", it just ignores and checks again in 2 seconds
            } catch (pollErr) {
              console.error("Error polling task status:", pollErr);
              clearInterval(pollInterval);
            }
          }, 2000); // Poll every 2000ms (2 seconds)
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

// src/services/websocket.js
import { useSystemStore } from "../store/useSystemStore";

let ws = null;

export const connectSystemWebSocket = () => {
  if (ws) return;

  // Connect to your FastAPI WebSocket endpoint
  ws = new WebSocket("ws://localhost:8000/api/stream/live");

  ws.onmessage = async (event) => {
    const data = JSON.parse(event.data);
    const store = useSystemStore.getState();

    // 1. SURGE DETECTED
    if (data.type === "TRAFFIC_SURGE") {
      // Instantly update the UI to show the surge location
      store.triggerSurgeResponse(data.payload);

      try {
        // 2. AUTOMATICALLY FIRE AI COPILOT & ROUTING ENGINE
        const response = await fetch(
          "http://localhost:8000/api/copilot/generate",
          {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              event_cause: data.payload.event_cause,
              corridor: data.payload.corridor,
              expected_crowd: data.payload.estimated_impact,
              event_datetime: new Date().toISOString(),
            }),
          },
        );

        const result = await response.json();

        // 3. PLOT BARRICADES AND RENDER GEMINI TEXT ON THE MAP
        store.resolveSurgeResponse(
          result.operational_order,
          result.barricades || [],
          result.diversion_routes || null,
        );
      } catch (error) {
        console.error("Automated Copilot execution failed:", error);
      }
    }
  };

  ws.onclose = () => {
    ws = null;
    setTimeout(connectSystemWebSocket, 3000); // Auto-reconnect
  };
};

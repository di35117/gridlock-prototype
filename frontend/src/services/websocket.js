import { useSystemStore } from "../store/useSystemStore";

const RAW_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

// CENTRALIZED DEFENSIVE LAYER: Forces absolute protocols and cleans trailing slashes
export const SAFE_API_URL = (() => {
  let url = RAW_URL.trim();
  if (!url.startsWith("http://") && !url.startsWith("https://")) {
    url =
      url.includes("localhost") || url.includes("127.0.0.1")
        ? `http://${url}`
        : `https://${url}`;
  }
  return url.endsWith("/") ? url.slice(0, -1) : url;
})();

// Automatically convert the secure or standard http protocol into sockets cleanly
const WS_URL =
  SAFE_API_URL.replace("https://", "wss://").replace("http://", "ws://") +
  "/api/ws/dashboard";

let ws = null;

export const connectSystemWebSocket = () => {
  if (ws) return;

  ws = new WebSocket(WS_URL);

  ws.onmessage = async (event) => {
    try {
      const data = JSON.parse(event.data);
      const store = useSystemStore.getState();

      // 1. Log every telemetry point directly into the Live Feed component
      store.addIntelAlert(data);

      // 2. Automated Trigger Condition: Capture active alerts or anomalies
      if (
        data.type === "TRAFFIC_SURGE" ||
        data.type === "CCTV_ANOMALY" ||
        data.risk_level === "Critical" ||
        data.risk_level === "High"
      ) {
        // Refocus dashboard UI and trigger global processing state instantly
        store.triggerSurgeResponse(data);

        try {
          logger.info(
            "[WebSocket] Initiating AI Copilot execution payload submission...",
          );

          // Map incoming websocket schema fields into standard Copilot request parameters
          const requestPayload = {
            event_cause: data.event_cause || "traffic_congestion",
            corridor: data.corridor || "unknown_corridor",
            expected_crowd: parseInt(data.expected_crowd || 1200, 10),
            event_details:
              data.message || "Automated threshold anomaly trigger.",
            event_datetime: new Date().toISOString(),
            latitude: parseFloat(data.latitude || 12.9716),
            longitude: parseFloat(data.longitude || 77.5946),
          };

          // POST request to Celery hand-off endpoint (Guaranteed 200ms quick response)
          const response = await fetch(`${SAFE_API_URL}/api/copilot/generate`, {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
            },
            body: JSON.stringify(requestPayload),
          });

          // Defensive HTML response check to intercept 404/502 custom web pages before JSON parsing crashes
          const contentType = response.headers.get("content-type");
          if (
            !response.ok ||
            !contentType ||
            !contentType.includes("application/json")
          ) {
            const errorText = await response.text();
            throw new Error(
              `Server returned invalid response structure. Status: ${response.status}. Snippet: ${errorText.slice(0, 50)}`,
            );
          }

          const taskData = await response.json();
          const targetTaskId = taskData.task_id;

          // 3. BACKGROUND TASK POLLING METRIC: Poll the task status until complete
          const pollInterval = setInterval(async () => {
            try {
              const statusResponse = await fetch(
                `${SAFE_API_URL}/api/copilot/status/${targetTaskId}`,
              );

              if (!statusResponse.ok) {
                throw new Error(
                  `Status polling network anomaly: ${statusResponse.status}`,
                );
              }

              const statusData = await statusResponse.json();

              if (statusData.status === "completed") {
                clearInterval(pollInterval);

                let finalBarricades = [];
                if (statusData.barricades) {
                  finalBarricades = Object.values(statusData.barricades);
                }

                // Hydrate the store with the completed background metrics
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
                  "⚠️ Asynchronous tactical operational plan compilation failed on worker thread.",
                  [],
                  null,
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
              store.resolveSurgeResponse(
                "⚠️ Target background tracking task became unreachable.",
                [],
                null,
                null,
                null,
              );
            }
          }, 2000);
        } catch (error) {
          console.error("Automated Copilot execution failed:", error);
          store.resolveSurgeResponse(
            `Failed to communicate with AI Copilot service: ${error.message}`,
            [],
            null,
            null,
            null,
          );
        }
      }
    } catch (parseErr) {
      console.error("Malformed root websocket event frame dropped:", parseErr);
    }
  };

  ws.onclose = () => {
    ws = null;
    setTimeout(connectSystemWebSocket, 3000); // Trigger clean auto-reconnect tracking loop
  };
};

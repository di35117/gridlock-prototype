import React, { useState, useEffect, useRef } from "react";
import { mappls } from "mappls-web-maps";
import { useSystemStore } from "../store/useSystemStore";
import { ShieldAlert, AlertTriangle, Loader2 } from "lucide-react";

const MAPMYINDIA_TOKEN = import.meta.env.VITE_MAPMYINDIA_SDK_KEY;

export default function BengaluruMap() {
  const {
    roadMetrics,
    activeSurge,
    barricades,
    diversions,
    setRoadMetrics,
    isProcessing,
  } = useSystemStore();

  const [isMapLoading, setIsMapLoading] = useState(true);
  const [mapInstance, setMapInstance] = useState(null); // Tracks active map cleanly across renders
  const initializationRef = useRef(false); // Protects against React 18 double execution

  // 1. Robust Backend Network Fetching
  useEffect(() => {
    const fetchMetrics = async () => {
      try {
        let rawUrl =
          import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

        if (!rawUrl.startsWith("http://") && !rawUrl.startsWith("https://")) {
          rawUrl = `https://${rawUrl}`;
        }

        const endpoint = `${rawUrl}/api/routing/network/metrics`;
        const res = await fetch(endpoint);

        if (!res.ok) {
          throw new Error(`Server rejected request with status: ${res.status}`);
        }

        const data = await res.json();
        setRoadMetrics(data);
      } catch (err) {
        console.error("Failed to load road metrics:", err.message);
      }
    };
    if (!roadMetrics) fetchMetrics();
  }, [roadMetrics, setRoadMetrics]);

  // 2. Safe, Isolated Mappls SDK Initialization
  useEffect(() => {
    if (!MAPMYINDIA_TOKEN) {
      console.error(
        "Missing VITE_MAPMYINDIA_SDK_KEY in environment variables.",
      );
      return;
    }

    if (initializationRef.current) return;
    initializationRef.current = true;

    const mapplsSdk = new mappls();

    mapplsSdk.initialize(MAPMYINDIA_TOKEN, { map: true }, () => {
      // Safety guard to ensure target DOM element is mounted
      if (!document.getElementById("mapmyindia-container")) return;

      const mapObject = mapplsSdk.Map({
        id: "mapmyindia-container",
        properties: {
          // ⚠️ FIXED: MapmyIndia vector engine strictly uses standard GeoJSON [Longitude, Latitude]
          center: [77.5946, 12.9716],
          zoom: 12.5,
          theme: "dark",
          zoomControl: true,
          location: true,
        },
      });

      // Catch silent vector layout errors
      mapObject.on("error", (e) => {
        console.error("MapmyIndia Vector Engine Error:", e);
      });

      mapObject.on("load", () => {
        setMapInstance(mapObject);
        setIsMapLoading(false);
      });
    });

    return () => {
      if (mapInstance) {
        mapInstance.remove();
      }
      initializationRef.current = false;
    };
  }, []);

  // 3. Cinematic Camera Sweeps upon Emergency Events
  useEffect(() => {
    if (activeSurge && mapInstance && !isMapLoading) {
      mapInstance.flyTo({
        center: [
          activeSurge.longitude || 77.5383,
          activeSurge.latitude || 12.9562,
        ],
        zoom: 16,
        pitch: 65,
        bearing: 25,
        duration: 2500,
      });
    }
  }, [activeSurge, mapInstance, isMapLoading]);

  // 4. Map Data Layers (Road Vectors, Diversions, Heatmaps)
  useEffect(() => {
    if (!mapInstance || isMapLoading) return;

    // --- A. THERMAL ROAD HEATMAP ---
    if (roadMetrics) {
      if (mapInstance.getSource("bengaluru-roads")) {
        mapInstance.getSource("bengaluru-roads").setData(roadMetrics);
      } else {
        mapInstance.addSource("bengaluru-roads", {
          type: "geojson",
          data: roadMetrics,
        });
        mapInstance.addLayer({
          id: "thermal-heat-layer",
          type: "line",
          source: "bengaluru-roads",
          filter: [">=", ["get", "risk_score"], 0.4],
          paint: {
            "line-width": ["interpolate", ["linear"], ["zoom"], 10, 15, 15, 40],
            "line-blur": ["interpolate", ["linear"], ["zoom"], 10, 15, 15, 30],
            "line-opacity": 0.65,
            "line-color": [
              "interpolate",
              ["linear"],
              ["get", "risk_score"],
              0.4,
              "rgba(234, 179, 8, 0)",
              0.6,
              "#eab308",
              0.8,
              "#f97316",
              1.0,
              "#ef4444",
            ],
          },
        });
      }
    }

    // --- B. AI TACTICAL DIVERSION ROUTES ---
    if (diversions) {
      if (mapInstance.getSource("ai-diversions")) {
        mapInstance.getSource("ai-diversions").setData(diversions);
      } else {
        mapInstance.addSource("ai-diversions", {
          type: "geojson",
          data: diversions,
        });
        mapInstance.addLayer({
          id: "ai-route",
          type: "line",
          source: "ai-diversions",
          paint: {
            "line-color": "#3b82f6",
            "line-width": 6,
            "line-dasharray": [2, 2],
            "line-opacity": isProcessing ? 0.4 : 1.0,
          },
        });
      }
    } else {
      if (mapInstance.getLayer("ai-route")) mapInstance.removeLayer("ai-route");
      if (mapInstance.getSource("ai-diversions"))
        mapInstance.removeSource("ai-diversions");
    }

    // --- C. BREATHING INCIDENT HEATMAP ---
    if (activeSurge && activeSurge.status !== "resolved") {
      const intensity = activeSurge.z_score
        ? Math.min(activeSurge.z_score / 2, 1)
        : 0.8;
      const heatmapData = {
        type: "FeatureCollection",
        features: [
          {
            type: "Feature",
            geometry: {
              type: "Point",
              coordinates: [
                activeSurge.longitude || 77.5383,
                activeSurge.latitude || 12.9562,
              ],
            },
            properties: { risk: intensity },
          },
        ],
      };

      if (mapInstance.getSource("surge-heatmap")) {
        mapInstance.getSource("surge-heatmap").setData(heatmapData);
      } else {
        mapInstance.addSource("surge-heatmap", {
          type: "geojson",
          data: heatmapData,
        });
        mapInstance.addLayer({
          id: "surge-heatmap-layer",
          type: "heatmap",
          source: "surge-heatmap",
          paint: {
            "heatmap-weight": [
              "interpolate",
              ["linear"],
              ["get", "risk"],
              0,
              0,
              1,
              1,
            ],
            "heatmap-color": [
              "interpolate",
              ["linear"],
              ["heatmap-density"],
              0,
              "rgba(0,0,0,0)",
              0.5,
              "#eab308",
              1,
              "#ef4444",
            ],
            "heatmap-radius": [
              "interpolate",
              ["linear"],
              ["zoom"],
              10,
              15,
              15,
              60,
            ],
            "heatmap-opacity": 0.8,
          },
        });
      }
    } else {
      if (mapInstance.getLayer("surge-heatmap-layer"))
        mapInstance.removeLayer("surge-heatmap-layer");
      if (mapInstance.getSource("surge-heatmap"))
        mapInstance.removeSource("surge-heatmap");
    }
  }, [
    roadMetrics,
    diversions,
    activeSurge,
    isProcessing,
    mapInstance,
    isMapLoading,
  ]);

  return (
    <div className="w-full h-full relative bg-gray-950 overflow-hidden">
      {isMapLoading && (
        <div className="absolute inset-0 z-50 flex flex-col items-center justify-center bg-gray-950/80 backdrop-blur-sm">
          <Loader2 className="w-8 h-8 text-blue-500 animate-spin mb-3" />
          <h3 className="text-gray-300 font-mono text-sm tracking-widest font-bold">
            INITIALIZING MAPMYINDIA CORE...
          </h3>
        </div>
      )}

      <div
        id="mapmyindia-container"
        className="absolute inset-0 w-full h-full"
      />

      {/* EMERGENCY SURGE PIN MARKER */}
      {!isMapLoading && mapInstance && activeSurge && (
        <CustomMapMarker
          map={mapInstance}
          longitude={activeSurge.longitude || 77.5383}
          latitude={activeSurge.latitude || 12.9562}
        >
          <div className="relative flex items-center justify-center">
            <div className="absolute w-16 h-16 bg-red-600/20 rounded-full animate-ping"></div>
            <div className="bg-red-950 border-2 border-red-500 p-2 rounded-full shadow-[0_0_30px_rgba(239,68,68,1)] z-10">
              <AlertTriangle className="text-red-500" size={28} />
            </div>
          </div>
        </CustomMapMarker>
      )}

      {/* DYNAMIC BARRICADE MARKERS */}
      {!isMapLoading &&
        mapInstance &&
        barricades &&
        barricades.map((coord, idx) => (
          <CustomMapMarker
            key={`barricade-${idx}`}
            map={mapInstance}
            longitude={coord[0]}
            latitude={coord[1]}
          >
            <div className="relative flex items-center justify-center group cursor-pointer">
              <div className="absolute inset-0 bg-yellow-500/50 blur-md rounded-full animate-pulse"></div>
              <div className="relative bg-gray-950 border border-yellow-500 text-yellow-500 px-2 py-1 rounded shadow-lg flex items-center gap-2 z-10 transform hover:scale-110 transition-transform">
                <ShieldAlert size={14} />
                <span className="text-[10px] font-mono font-bold tracking-wider whitespace-nowrap">
                  ROAD CLOSED
                </span>
              </div>
            </div>
          </CustomMapMarker>
        ))}
    </div>
  );
}

// 5. Bulletproof Screen Projection Anchor Component
function CustomMapMarker({ map, longitude, latitude, children }) {
  const [position, setPosition] = useState({ x: -1000, y: -1000 });

  useEffect(() => {
    if (!map) return;

    const updatePosition = () => {
      if (
        longitude == null ||
        latitude == null ||
        isNaN(longitude) ||
        isNaN(latitude)
      ) {
        return;
      }

      try {
        const pos = map.project([longitude, latitude]);
        if (pos && pos.x !== undefined && pos.y !== undefined) {
          setPosition({ x: pos.x, y: pos.y });
        }
      } catch (err) {
        // Suppress quiet frame layout delays during initialization fly-ins
      }
    };

    updatePosition();
    map.on("move", updatePosition);
    map.on("zoom", updatePosition);

    return () => {
      map.off("move", updatePosition);
      map.off("zoom", updatePosition);
    };
  }, [map, longitude, latitude]);

  return (
    <div
      style={{
        position: "absolute",
        left: position.x,
        top: position.y,
        transform: "translate(-50%, -50%)",
        pointerEvents: "none",
        zIndex: 20,
      }}
    >
      <div style={{ pointerEvents: "auto" }}>{children}</div>
    </div>
  );
}

import React, { useState, useEffect, useRef } from "react";
import { mappls } from "mappls-web-maps";
import { useSystemStore } from "../store/useSystemStore";
import { ShieldAlert, AlertTriangle, Loader2 } from "lucide-react";

const MAPMYINDIA_TOKEN = import.meta.env.VITE_MAPMYINDIA_SDK_KEY;

// 1. Initialize the Mappls Class Object globally for the component
const mapplsClassObject = new mappls();

let sharedMapInstance = null;

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
  const [mapRenderTrigger, setMapRenderTrigger] = useState(0);
  const mapRef = useRef(null);

  // Fetch initial road metrics
  useEffect(() => {
    const fetchMetrics = async () => {
      try {
        const API_URL =
          import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";
        const res = await fetch(`${API_URL}/api/routing/network/metrics`);
        const data = await res.json();
        setRoadMetrics(data);
      } catch (err) {
        console.error("Failed to load road metrics", err);
      }
    };
    if (!roadMetrics) fetchMetrics();
  }, [roadMetrics, setRoadMetrics]);

  // 2. Correct NPM Package Initialization
  useEffect(() => {
    if (!MAPMYINDIA_TOKEN) {
      console.error(
        "Missing VITE_MAPMYINDIA_SDK_KEY in environment variables.",
      );
      return;
    }

    // Pass { map: true } to load the core map library
    mapplsClassObject.initialize(MAPMYINDIA_TOKEN, { map: true }, () => {
      // Use the class method .Map() and nest settings inside 'properties'
      const mapObject = mapplsClassObject.Map({
        id: "mapmyindia-container",
        properties: {
          center: [12.9716, 77.5946],
          zoom: 12.5,
          theme: "dark",
          zoomControl: true,
          location: true,
        },
      });

      mapObject.on("load", () => {
        mapRef.current = mapObject;
        sharedMapInstance = mapObject;
        setIsMapLoading(false);
        setMapRenderTrigger((prev) => prev + 1);
      });
    });

    return () => {
      if (mapRef.current) mapRef.current.remove();
      sharedMapInstance = null;
    };
  }, []);

  // Cinematic Camera Sweeps
  useEffect(() => {
    if (activeSurge && mapRef.current && !isMapLoading) {
      mapRef.current.flyTo({
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
  }, [activeSurge, isMapLoading]);

  // Map Data Layers (Roads, Diversions, Heatmaps)
  useEffect(() => {
    const map = mapRef.current;
    if (!map || isMapLoading) return;

    // --- A. THERMAL ROAD HEATMAP ---
    if (roadMetrics) {
      if (map.getSource("bengaluru-roads")) {
        map.getSource("bengaluru-roads").setData(roadMetrics);
      } else {
        map.addSource("bengaluru-roads", {
          type: "geojson",
          data: roadMetrics,
        });
        map.addLayer({
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
      if (map.getSource("ai-diversions")) {
        map.getSource("ai-diversions").setData(diversions);
      } else {
        map.addSource("ai-diversions", { type: "geojson", data: diversions });
        map.addLayer({
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
      if (map.getLayer("ai-route")) map.removeLayer("ai-route");
      if (map.getSource("ai-diversions")) map.removeSource("ai-diversions");
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

      if (map.getSource("surge-heatmap")) {
        map.getSource("surge-heatmap").setData(heatmapData);
      } else {
        map.addSource("surge-heatmap", { type: "geojson", data: heatmapData });
        map.addLayer({
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
      if (map.getLayer("surge-heatmap-layer"))
        map.removeLayer("surge-heatmap-layer");
      if (map.getSource("surge-heatmap")) map.removeSource("surge-heatmap");
    }
  }, [roadMetrics, diversions, activeSurge, isProcessing, isMapLoading]);

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

      {/* FIXED DOM MARKERS OVERLAY */}
      {!isMapLoading && activeSurge && (
        <CustomMapMarker
          mapTrigger={mapRenderTrigger}
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

      {!isMapLoading &&
        barricades &&
        barricades.map((coord, idx) => (
          <CustomMapMarker
            key={`barricade-${idx}`}
            mapTrigger={mapRenderTrigger}
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

// Custom Map Marker Helper
function CustomMapMarker({ mapTrigger, longitude, latitude, children }) {
  const [position, setPosition] = useState({ x: -1000, y: -1000 });

  useEffect(() => {
    const map = sharedMapInstance;
    if (!map) return;

    const updatePosition = () => {
      const pos = map.project([longitude, latitude]);
      setPosition({ x: pos.x, y: pos.y });
    };

    updatePosition();
    map.on("move", updatePosition);
    map.on("zoom", updatePosition);

    return () => {
      map.off("move", updatePosition);
      map.off("zoom", updatePosition);
    };
  }, [mapTrigger, longitude, latitude]);

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

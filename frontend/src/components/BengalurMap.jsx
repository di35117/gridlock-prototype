import React, { useState, useEffect, useRef } from "react";
import { mappls } from "mappls-web-maps";
import { useSystemStore } from "../store/useSystemStore";
import { ShieldAlert, AlertTriangle, Loader2 } from "lucide-react";

const MAPMYINDIA_TOKEN = import.meta.env.VITE_MAPMYINDIA_SDK_KEY;

// 1. Initialize Mappls Class safely outside the component
const mapplsClassObject = new mappls();

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
  const [mapInstance, setMapInstance] = useState(null);
  const mapContainerRef = useRef(null);

  // Fetch metrics if WebSocket hasn't already populated them
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
        if (res.ok) {
          const data = await res.json();
          setRoadMetrics(data);
        }
      } catch (err) {
        console.warn("Fetch skipped/failed, relying on WebSocket data.");
      }
    };
    if (!roadMetrics) fetchMetrics();
  }, [roadMetrics, setRoadMetrics]);

  // 2. The Bulletproof MapmyIndia Initializer
  useEffect(() => {
    if (!MAPMYINDIA_TOKEN) {
      console.error(
        "Missing VITE_MAPMYINDIA_SDK_KEY in environment variables.",
      );
      return;
    }

    let mapObject = null;
    let isCancelled = false; // Strict Mode Guard

    // CRITICAL: `map: true` is mandatory to inject the actual map canvas
    const loadOptions = {
      map: true,
      libraries: [],
      plugins: [],
    };

    mapplsClassObject.initialize(MAPMYINDIA_TOKEN, loadOptions, () => {
      // If React unmounted this component before the Mappls script finished downloading, abort.
      if (isCancelled || !mapContainerRef.current) return;

      mapObject = mapplsClassObject.Map({
        id: mapContainerRef.current.id,
        properties: {
          center: [12.9716, 77.5946], // [Latitude, Longitude]
          zoom: 12.5,
          theme: "dark",
          zoomControl: true,
          // Removed 'location: true' to prevent browser GPS prompt from freezing initialization
        },
      });

      mapObject.on("load", () => {
        setMapInstance(mapObject);
        setIsMapLoading(false);
      });

      mapObject.on("error", (e) => {
        console.error("MapmyIndia Graphics Engine Error:", e);
      });
    });

    return () => {
      isCancelled = true;
      if (mapObject) {
        mapObject.remove();
      }
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

  // 4. Map Data Layers Overlay logic
  useEffect(() => {
    if (!mapInstance || isMapLoading) return;

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

      {/* Linked via Ref instead of static ID to guarantee React DOM synchronization */}
      <div
        id="mapmyindia-container"
        ref={mapContainerRef}
        className="absolute inset-0 w-full h-full"
      />

      {/* TACTICAL EMERGENCY PIN */}
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

      {/* TACTICAL ROAD BARRICADES */}
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

// 5. Dynamic Screen Projection Synchronizer
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
      )
        return;

      try {
        const pos = map.project([longitude, latitude]);
        if (pos && pos.x !== undefined && pos.y !== undefined) {
          setPosition({ x: pos.x, y: pos.y });
        }
      } catch (err) {}
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

import React, { useState, useEffect, useRef, useMemo } from "react";
import Map, {
  Source,
  Layer,
  Marker,
  NavigationControl,
} from "react-map-gl/maplibre";
import { useSystemStore } from "../store/useSystemStore";
import { ShieldAlert, AlertTriangle, Loader2 } from "lucide-react";
import "maplibre-gl/dist/maplibre-gl.css";

const MAPTILER_TOKEN = import.meta.env.VITE_MAPTILER_TOKEN;

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
  const mapRef = useRef(null);

  const [viewState, setViewState] = useState({
    longitude: 77.5946,
    latitude: 12.9716,
    zoom: 12.5,
    pitch: 45,
    bearing: 0,
  });

  useEffect(() => {
    const fetchMetrics = async () => {
      setIsMapLoading(true);
      try {
        const res = await fetch(
          "http://localhost:8000/api/routing/network/metrics",
        );
        const data = await res.json();
        setRoadMetrics(data);
      } catch (err) {
        console.error("Failed to load road metrics", err);
      } finally {
        setIsMapLoading(false);
      }
    };
    if (!roadMetrics) fetchMetrics();
  }, [roadMetrics, setRoadMetrics]);

  // Cinematic Camera Sweeps
  useEffect(() => {
    if (activeSurge && mapRef.current) {
      mapRef.current.flyTo({
        center: [activeSurge.longitude, activeSurge.latitude],
        zoom: 16,
        pitch: 65,
        bearing: 25,
        duration: 2500,
        essential: true,
      });
    }
  }, [activeSurge]);

  // --- THE WEATHER RADAR / THERMAL HEATMAP ---
  const thermalHeatStyle = useMemo(
    () => ({
      id: "thermal-heat-layer",
      type: "line",
      // 1. The Stealth Filter: Completely hides safe roads (Removes the Neon Green)
      filter: [">=", ["get", "risk_score"], 0.4],
      paint: {
        // 2. Massive width to create overlapping "clouds" instead of sharp lines
        "line-width": ["interpolate", ["linear"], ["zoom"], 10, 15, 15, 40],
        // 3. Extreme blur to melt the geometries together
        "line-blur": ["interpolate", ["linear"], ["zoom"], 10, 15, 15, 30],
        "line-opacity": 0.65,
        "line-color": [
          "interpolate",
          ["linear"],
          ["get", "risk_score"],
          0.4,
          "rgba(234, 179, 8, 0)", // Invisible transition
          0.6,
          "#eab308", // Yellow (Warning)
          0.8,
          "#f97316", // Orange (High Risk)
          1.0,
          "#ef4444", // Red (Critical)
        ],
      },
    }),
    [],
  );

  // THE ON-DEMAND SCANNER (The sharp AI route when an incident occurs)
  const diversionStyle = useMemo(
    () => ({
      id: "ai-route",
      type: "line",
      paint: {
        "line-color": "#3b82f6",
        "line-width": 6,
        "line-dasharray": [2, 2],
        "line-opacity": isProcessing ? 0.4 : 1.0,
      },
    }),
    [isProcessing],
  );

  if (!MAPTILER_TOKEN)
    return (
      <div className="text-white p-4 font-mono">Missing MapTiler Token</div>
    );

  return (
    <div className="w-full h-full relative bg-gray-950">
      {isMapLoading && (
        <div className="absolute inset-0 z-50 flex items-center justify-center bg-gray-950/80 backdrop-blur-sm">
          <div className="flex flex-col items-center p-6 bg-gray-900 rounded-lg border border-gray-800 shadow-2xl">
            <Loader2 className="w-8 h-8 text-blue-500 animate-spin mb-3" />
            <h3 className="text-gray-300 font-mono text-sm tracking-widest font-bold">
              DECOMPRESSING ML MATRICES
            </h3>
          </div>
        </div>
      )}

      <Map
        ref={mapRef}
        {...viewState}
        onMove={(evt) => setViewState(evt.viewState)}
        mapStyle={`https://api.maptiler.com/maps/dataviz-dark/style.json?key=${MAPTILER_TOKEN}`}
      >
        <NavigationControl position="bottom-right" />

        {/* The Predictive Weather Radar */}
        {roadMetrics && (
          <Source id="bengaluru-roads" type="geojson" data={roadMetrics}>
            <Layer {...thermalHeatStyle} />
          </Source>
        )}

        {/* The Tactical Blue Divert Line */}
        {diversions && (
          <Source id="ai-diversions" type="geojson" data={diversions}>
            <Layer {...diversionStyle} />
          </Source>
        )}

        {/* The Incident Ground-Zero Pulse */}
        {activeSurge && (
          <Marker
            longitude={activeSurge.longitude}
            latitude={activeSurge.latitude}
          >
            <div className="relative flex items-center justify-center">
              <div className="absolute w-16 h-16 bg-red-600/20 rounded-full animate-ping"></div>
              <div className="bg-red-950 border-2 border-red-500 p-2 rounded-full shadow-[0_0_30px_rgba(239,68,68,1)] z-10">
                <AlertTriangle className="text-red-500" size={28} />
              </div>
            </div>
          </Marker>
        )}

        {/* --- TACTICAL BARRICADE OVERLAY --- */}
        {barricades.map((coord, idx) => (
          <Marker
            key={`barricade-${idx}`}
            longitude={coord[0]}
            latitude={coord[1]}
          >
            <div className="relative flex items-center justify-center group cursor-pointer">
              {/* Glowing forcefield effect */}
              <div className="absolute inset-0 bg-yellow-500/50 blur-md rounded-full animate-pulse"></div>
              {/* Physical barricade UI */}
              <div className="relative bg-gray-950 border border-yellow-500 text-yellow-500 px-2 py-1 rounded shadow-lg flex items-center gap-2 z-10 transform hover:scale-110 transition-transform">
                <ShieldAlert size={14} />
                <span className="text-[10px] font-mono font-bold tracking-wider whitespace-nowrap">
                  ROAD CLOSED
                </span>
              </div>
            </div>
          </Marker>
        ))}
      </Map>
    </div>
  );
}

// src/components/BengaluruMap.jsx
import React, { useState, useEffect } from "react";
import Map, {
  Source,
  Layer,
  Marker,
  NavigationControl,
} from "react-map-gl/maplibre";
import { useSystemStore } from "../store/useSystemStore";
import { ShieldAlert, AlertTriangle } from "lucide-react";
import "maplibre-gl/dist/maplibre-gl.css";

const MAPTILER_TOKEN = import.meta.env.VITE_MAPTILER_TOKEN;

export default function BengaluruMap() {
  const { roadMetrics, activeSurge, barricades, diversions, setRoadMetrics } =
    useSystemStore();

  const [viewState, setViewState] = useState({
    longitude: 77.5946,
    latitude: 12.9716,
    zoom: 12,
    pitch: 45,
    bearing: 0,
  });

  // Load ML Road Metrics on Startup
  useEffect(() => {
    fetch("http://localhost:8000/api/network/metrics")
      .then((res) => res.json())
      .then((data) => setRoadMetrics(data))
      .catch((err) => console.error("Failed to load road metrics", err));
  }, []);

  // Data-Driven Styling: Colors roads based on the ML 'risk_score' (0.0 to 1.0)
  const roadRiskStyle = {
    id: "road-risk-layer",
    type: "line",
    paint: {
      "line-width": ["interpolate", ["linear"], ["zoom"], 10, 2, 15, 6],
      "line-color": [
        "interpolate",
        ["linear"],
        ["get", "risk_score"],
        0.0,
        "#22c55e", // Green (Safe)
        0.5,
        "#eab308", // Yellow (Warning)
        0.8,
        "#f97316", // Orange (High Risk)
        1.0,
        "#ef4444", // Red (Critical)
      ],
    },
  };

  if (!MAPTILER_TOKEN)
    return <div className="text-white p-4">Missing MapTiler Token</div>;

  return (
    <div className="w-full h-full relative bg-gray-950">
      <Map
        {...viewState}
        onMove={(evt) => setViewState(evt.viewState)}
        mapStyle={`https://api.maptiler.com/maps/dataviz-dark/style.json?key=${MAPTILER_TOKEN}`}
      >
        <NavigationControl position="bottom-right" />

        {/* 1. The ML Road Network */}
        {roadMetrics && (
          <Source id="bengaluru-roads" type="geojson" data={roadMetrics}>
            <Layer {...roadRiskStyle} />
          </Source>
        )}

        {/* 2. Automated Diversion Routes */}
        {diversions && (
          <Source id="ai-diversions" type="geojson" data={diversions}>
            <Layer
              id="diversion-lines"
              type="line"
              paint={{
                "line-color": "#3b82f6",
                "line-width": 4,
                "line-dasharray": [2, 2],
              }}
            />
          </Source>
        )}

        {/* 3. Primary Surge Location */}
        {activeSurge && (
          <Marker
            longitude={activeSurge.longitude}
            latitude={activeSurge.latitude}
          >
            <div className="animate-pulse bg-red-600/20 p-2 rounded-full border border-red-500">
              <AlertTriangle className="text-red-500" size={24} />
            </div>
          </Marker>
        )}

        {/* 4. Automated Barricade Placements */}
        {barricades.map((coord, idx) => (
          <Marker
            key={`barricade-${idx}`}
            longitude={coord[0]}
            latitude={coord[1]}
          >
            <div className="bg-yellow-500/20 border-2 border-yellow-500 rounded p-1">
              <ShieldAlert size={16} className="text-yellow-500" />
            </div>
          </Marker>
        ))}
      </Map>
    </div>
  );
}

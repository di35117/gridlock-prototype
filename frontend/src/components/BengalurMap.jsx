// src/components/BengaluruMap.jsx
import React, { useState, useEffect } from "react";
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
  const { roadMetrics, activeSurge, barricades, diversions, setRoadMetrics } =
    useSystemStore();
  const [isMapLoading, setIsMapLoading] = useState(true);

  const [viewState, setViewState] = useState({
    longitude: 77.5946,
    latitude: 12.9716,
    zoom: 11.5, // Slightly zoomed in for a better initial view
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

    fetchMetrics();

    if (activeSurge) {
      const timer = setTimeout(() => {
        fetchMetrics();
      }, 500);
      return () => clearTimeout(timer);
    }
  }, [activeSurge, setRoadMetrics]);

  // 1. Sleeker, Tactical Data-Driven Styling
  const roadRiskStyle = {
    id: "road-risk-layer",
    type: "line",
    paint: {
      // Scale smoothly: incredibly thin at high altitudes, thicker at street level
      "line-width": [
        "interpolate",
        ["linear"],
        ["zoom"],
        10,
        0.5, // Very thin when zoomed out
        13,
        2, // Medium at neighborhood level
        16,
        5, // Thick at street level
      ],
      // Drop the opacity slightly so overlapping roads blend instead of clash
      "line-opacity": 0.75,
      // Slightly muted, tactical colors instead of pure neon
      "line-color": [
        "interpolate",
        ["linear"],
        ["get", "risk_score"],
        0.0,
        "#22c55e", // Green
        0.5,
        "#fbbf24", // Muted Amber
        0.8,
        "#f97316", // Orange
        1.0,
        "#dc2626", // Deep Red
      ],
    },
  };

  if (!MAPTILER_TOKEN)
    return (
      <div className="text-white p-4 font-mono text-sm">
        Missing MapTiler Token
      </div>
    );

  return (
    <div className="w-full h-full relative bg-gray-950">
      {/* 2. Loading State Overlay for UX */}
      {isMapLoading && (
        <div className="absolute inset-0 z-50 flex items-center justify-center bg-gray-950/80 backdrop-blur-sm">
          <div className="flex flex-col items-center p-6 bg-gray-900 rounded-lg border border-gray-800 shadow-2xl">
            <Loader2 className="w-8 h-8 text-blue-500 animate-spin mb-3" />
            <h3 className="text-gray-300 font-mono text-sm tracking-widest font-bold">
              INGESTING ML ROAD METRICS
            </h3>
            <p className="text-gray-500 text-xs font-mono mt-1">
              Parsing GeoJSON payload...
            </p>
          </div>
        </div>
      )}

      <Map
        {...viewState}
        onMove={(evt) => setViewState(evt.viewState)}
        mapStyle={`https://api.maptiler.com/maps/dataviz-dark/style.json?key=${MAPTILER_TOKEN}`}
        interactiveLayerIds={["road-risk-layer"]} // Improves performance
      >
        <NavigationControl position="bottom-right" />

        {roadMetrics && (
          <Source
            id="bengaluru-roads"
            type="geojson"
            data={roadMetrics}
            generateId={true}
          >
            <Layer {...roadRiskStyle} />
          </Source>
        )}

        {diversions && (
          <Source id="ai-diversions" type="geojson" data={diversions}>
            <Layer
              id="diversion-lines"
              type="line"
              paint={{
                "line-color": "#3b82f6", // Bright blue for active AI routing
                "line-width": 4,
                "line-dasharray": [2, 2],
                "line-opacity": 0.9,
              }}
            />
          </Source>
        )}

        {activeSurge && (
          <Marker
            longitude={activeSurge.longitude}
            latitude={activeSurge.latitude}
          >
            <div className="animate-pulse bg-red-600/30 p-3 rounded-full border border-red-500 shadow-[0_0_15px_rgba(239,68,68,0.5)]">
              <AlertTriangle className="text-red-500" size={24} />
            </div>
          </Marker>
        )}

        {barricades.map((coord, idx) => (
          <Marker
            key={`barricade-${idx}`}
            longitude={coord[0]}
            latitude={coord[1]}
          >
            <div className="bg-yellow-500/20 border-2 border-yellow-500 rounded-sm p-1 shadow-[0_0_10px_rgba(234,179,8,0.3)]">
              <ShieldAlert size={16} className="text-yellow-500" />
            </div>
          </Marker>
        ))}
      </Map>
    </div>
  );
}

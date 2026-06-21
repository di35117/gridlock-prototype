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

  const roadGlowStyle = useMemo(
    () => ({
      id: "road-glow-layer",
      type: "line",
      paint: {
        "line-width": ["interpolate", ["linear"], ["zoom"], 10, 4, 15, 12],
        "line-blur": ["interpolate", ["linear"], ["zoom"], 10, 4, 15, 10],
        "line-opacity": 0.4,
        "line-color": [
          "interpolate",
          ["linear"],
          ["get", "risk_score"],
          0.0,
          "#22c55e",
          0.5,
          "#eab308",
          0.8,
          "#f97316",
          1.0,
          "#ef4444",
        ],
      },
    }),
    [],
  );

  const roadRiskStyle = useMemo(
    () => ({
      id: "road-risk-layer",
      type: "line",
      paint: {
        "line-width": ["interpolate", ["linear"], ["zoom"], 10, 1, 15, 4],
        "line-opacity": 0.9,
        "line-color": [
          "interpolate",
          ["linear"],
          ["get", "risk_score"],
          0.0,
          "#22c55e",
          0.5,
          "#eab308",
          0.8,
          "#f97316",
          1.0,
          "#ef4444",
        ],
      },
    }),
    [],
  );

  const roadLabelStyle = useMemo(
    () => ({
      id: "road-labels",
      type: "symbol",
      minzoom: 13,
      layout: {
        "symbol-placement": "line",
        "text-field": [
          "step",
          ["get", "risk_score"],
          "{name}",
          0.1,
          "{name} | RISK: {risk_score}",
        ],
        "text-size": 11,
        "text-letter-spacing": 0.1,
        "text-anchor": "center",
        "text-offset": [0, -1],
      },
      paint: {
        "text-color": [
          "interpolate",
          ["linear"],
          ["get", "risk_score"],
          0.0,
          "#9ca3af",
          0.5,
          "#fde047",
          0.8,
          "#fdba74",
          1.0,
          "#fca5a5",
        ],
        "text-halo-color": "#111827",
        "text-halo-width": 2,
      },
    }),
    [],
  );

  const diversionStyle = useMemo(
    () => ({
      id: "ai-route",
      type: "line",
      paint: {
        "line-color": "#3b82f6",
        "line-width": 5,
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
              DECOMPRESSING NETWORK GRAPH
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

        {roadMetrics && (
          <Source
            id="bengaluru-roads"
            type="geojson"
            data={roadMetrics}
            generateId={true}
          >
            <Layer {...roadGlowStyle} />
            <Layer {...roadRiskStyle} />
            <Layer {...roadLabelStyle} />
          </Source>
        )}

        {diversions && (
          <Source id="ai-diversions" type="geojson" data={diversions}>
            <Layer {...diversionStyle} />
          </Source>
        )}

        {activeSurge && (
          <Marker
            longitude={activeSurge.longitude}
            latitude={activeSurge.latitude}
          >
            <div className="relative flex items-center justify-center">
              <div className="absolute w-12 h-12 bg-red-600/30 rounded-full animate-ping"></div>
              <div className="bg-red-900 border border-red-500 p-2 rounded-full shadow-[0_0_20px_rgba(239,68,68,0.8)] z-10">
                <AlertTriangle className="text-red-400" size={24} />
              </div>
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

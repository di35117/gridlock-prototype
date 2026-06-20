import React, { useState } from "react";
import Map from "react-map-gl/maplibre";
import "maplibre-gl/dist/maplibre-gl.css"; // CRITICAL: Essential for layout positioning

const MAPTILER_TOKEN = import.meta.env.VITE_MAPTILER_TOKEN;

export default function BengaluruMap() {
  // Coordinates targeted exactly at Bengaluru center
  const [viewState, setViewState] = useState({
    longitude: 77.5946,
    latitude: 12.9716,
    zoom: 11,
    pitch: 45, // Retains the 3D Command Center perspective
    bearing: 0,
  });

  // Use a highly optimized vector dark mode style from MapTiler
  const mapStyleUrl = `https://api.maptiler.com/maps/toner-v2-dark/style.json?key=${MAPTILER_TOKEN}`;

  if (!MAPTILER_TOKEN) {
    return (
      <div className="flex-1 flex items-center justify-center bg-gray-900 text-red-400 p-6 text-center border border-gray-800">
        <div>
          <h2 className="text-xl font-bold mb-2">Missing MapTiler Key</h2>
          <p className="text-sm text-gray-400">
            Please add VITE_MAPTILER_TOKEN to your .env file and restart the
            server.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="w-full h-full relative">
      <Map
        {...viewState}
        onMove={(evt) => setViewState(evt.viewState)}
        mapStyle={mapStyleUrl}
        style={{ width: "100%", height: "100%" }}
      >
        {/* Geographic geojson layers, risk heatmaps, and markers will mount inside here */}
      </Map>

      {/* HUD Coordinate Tracker */}
      <div className="absolute top-4 left-4 bg-gray-900/90 border border-gray-700 text-[11px] font-mono px-3 py-1.5 rounded shadow-lg text-green-400 backdrop-blur-md pointer-events-none tracking-wider">
        SYS_LOC // LAT: {viewState.latitude.toFixed(4)} | LNG:{" "}
        {viewState.longitude.toFixed(4)}
      </div>
    </div>
  );
}

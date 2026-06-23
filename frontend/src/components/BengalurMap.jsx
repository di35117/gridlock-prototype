import React, { useState, useEffect, useRef } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { mappls } from "mappls-web-maps";
import { useSystemStore } from "../store/useSystemStore";
import { ShieldAlert, AlertTriangle, Loader2 } from "lucide-react";

const MAPMYINDIA_TOKEN = import.meta.env.VITE_MAPMYINDIA_SDK_KEY;

// Initialize Mappls Class safely outside the component
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

  // Manually track Mappls SDK Objects so we can destroy them on re-renders
  const roadLayerRefs = useRef([]);
  const diversionLayerRefs = useRef([]);
  const markerRefs = useRef([]);
  const heatmapRef = useRef(null);

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

  // 1. Initialize Mappls Engine
  useEffect(() => {
    if (!MAPMYINDIA_TOKEN) return;

    let mapObject = null;
    let isCancelled = false;

    mapplsClassObject.initialize(MAPMYINDIA_TOKEN, { map: true }, () => {
      if (isCancelled || !mapContainerRef.current) return;

      mapObject = mapplsClassObject.Map({
        id: mapContainerRef.current.id,
        properties: {
          center: [12.9716, 77.5946], // [lat, lng]
          zoom: 12.5,
          theme: "dark",
          zoomControl: true,
        },
      });

      mapObject.on("load", () => {
        setMapInstance(mapObject);
        setIsMapLoading(false);
      });
    });

    return () => {
      isCancelled = true;
      if (mapObject) mapObject.remove();
    };
  }, []);

  // 2. Camera Sweeps using Native Mappls Methods
  useEffect(() => {
    if (activeSurge && mapInstance && !isMapLoading) {
      const lat = activeSurge.latitude || 12.9562;
      const lng = activeSurge.longitude || 77.5383;

      // Replaced Mapbox flyTo with Mappls panTo/setZoom
      mapInstance.panTo({ lat, lng });
      mapInstance.setZoom(15);
    }
  }, [activeSurge, mapInstance, isMapLoading]);

  // 3. Discrete Layer Rendering (The Fix for Claude's Error)
  useEffect(() => {
    if (!mapInstance || isMapLoading) return;

    // --- CLEANUP PREVIOUS LAYERS ---
    roadLayerRefs.current.forEach((layer) => layer.remove());
    roadLayerRefs.current = [];

    diversionLayerRefs.current.forEach((layer) => layer.remove());
    diversionLayerRefs.current = [];

    markerRefs.current.forEach((marker) => marker.remove());
    markerRefs.current = [];

    if (heatmapRef.current) {
      heatmapRef.current.remove();
      heatmapRef.current = null;
    }

    // --- DRAW ROAD METRICS (Polylines instead of Mapbox Data-Driven Layers) ---
    if (roadMetrics && roadMetrics.features) {
      roadMetrics.features.forEach((feature) => {
        const risk = feature.properties.risk_score || 0;
        // Only draw high-risk roads to save DOM memory
        if (risk >= 0.4) {
          const path = feature.geometry.coordinates.map((c) => ({
            lat: c[1],
            lng: c[0],
          }));
          let color =
            risk >= 0.8 ? "#ef4444" : risk >= 0.6 ? "#f97316" : "#eab308";

          const polyline = new mapplsClassObject.Polyline({
            map: mapInstance,
            path: path,
            strokeColor: color,
            strokeWeight: 4,
            strokeOpacity: 0.65,
          });
          roadLayerRefs.current.push(polyline);
        }
      });
    }

    // --- DRAW AI DIVERSIONS ---
    if (diversions && diversions.features) {
      diversions.features.forEach((feature) => {
        const path = feature.geometry.coordinates.map((c) => ({
          lat: c[1],
          lng: c[0],
        }));
        const polyline = new mapplsClassObject.Polyline({
          map: mapInstance,
          path: path,
          strokeColor: "#3b82f6",
          strokeWeight: 6,
          strokeOpacity: isProcessing ? 0.4 : 1.0,
        });
        diversionLayerRefs.current.push(polyline);
      });
    }

    // --- DRAW BARRICADES (Using Mappls HTML Markers) ---
    if (barricades) {
      barricades.forEach((coord) => {
        const lng = coord.lon !== undefined ? coord.lon : coord[0];
        const lat = coord.lat !== undefined ? coord.lat : coord[1];

        // Convert React UI into a raw HTML string for the MapmyIndia engine
        const barricadeHtml = renderToStaticMarkup(
          <div className="relative flex items-center justify-center group cursor-pointer mt-4 ml-4">
            <div className="absolute inset-0 bg-yellow-500/50 blur-md rounded-full animate-pulse"></div>
            <div className="relative bg-gray-950 border border-yellow-500 text-yellow-500 px-2 py-1 rounded shadow-lg flex items-center gap-1 z-10">
              <ShieldAlert size={14} />
              <span className="text-[10px] font-mono font-bold whitespace-nowrap">
                CLOSED
              </span>
            </div>
          </div>,
        );

        const marker = new mapplsClassObject.Marker({
          map: mapInstance,
          position: { lat, lng },
          html: barricadeHtml,
        });
        markerRefs.current.push(marker);
      });
    }

    // --- DRAW SURGE EVENT PIN ---
    if (activeSurge && activeSurge.status !== "resolved") {
      const lat = activeSurge.latitude || 12.9562;
      const lng = activeSurge.longitude || 77.5383;

      const surgeHtml = renderToStaticMarkup(
        <div className="relative flex items-center justify-center mt-6 ml-6">
          <div className="absolute w-16 h-16 bg-red-600/20 rounded-full animate-ping"></div>
          <div className="bg-red-950 border-2 border-red-500 p-2 rounded-full shadow-[0_0_30px_rgba(239,68,68,1)] z-10">
            <AlertTriangle className="text-red-500" size={28} />
          </div>
        </div>,
      );

      const surgeMarker = new mapplsClassObject.Marker({
        map: mapInstance,
        position: { lat, lng },
        html: surgeHtml,
      });
      markerRefs.current.push(surgeMarker);

      // Fallback pseudo-heatmap using Mappls Circle (Native Heatmaps require specific Mappls plugins)
      const intensity = activeSurge.z_score
        ? Math.min(activeSurge.z_score / 2, 1)
        : 0.8;
      heatmapRef.current = new mapplsClassObject.Circle({
        map: mapInstance,
        center: { lat, lng },
        radius: 400 * intensity, // Meters
        fillColor: "#ef4444",
        fillOpacity: 0.3,
        strokeColor: "#ef4444",
        strokeOpacity: 0.8,
        strokeWeight: 1,
      });
    }
  }, [
    roadMetrics,
    diversions,
    barricades,
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
        ref={mapContainerRef}
        className="absolute inset-0 w-full h-full"
      />
    </div>
  );
}

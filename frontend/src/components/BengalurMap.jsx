import React, { useState, useEffect, useRef } from "react";
import maplibregl from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import { renderToStaticMarkup } from "react-dom/server";
import { useSystemStore } from "../store/useSystemStore";
import { SAFE_API_URL } from "../services/websocket";
import { ShieldAlert, Loader2 } from "lucide-react";

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
  const markersRef = useRef([]);

  // 1. Initial Data Foundation Network Load
  useEffect(() => {
    const fetchMetrics = async () => {
      try {
        const res = await fetch(`${SAFE_API_URL}/api/routing/network/metrics`);
        if (res.ok) {
          const data = await res.json();
          setRoadMetrics(data);
        }
      } catch (err) {
        console.error(
          "Failed to recover base road infrastructure parameters:",
          err,
        );
      }
    };
    fetchMetrics();
  }, [setRoadMetrics]);

  // 2. Instantiating Map Instance
  useEffect(() => {
    if (!mapContainerRef.current) return;

    const map = new maplibregl.Map({
      container: mapContainerRef.current,
      style: "https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json",
      center: [77.5946, 12.9716],
      zoom: 12,
      pitch: 30,
    });

    map.on("load", () => {
      setIsMapLoading(false);
      setMapInstance(map);
    });

    return () => map.remove();
  }, []);

  // 3. Dynamic Tactical Vector Overlays & Barricades Drawing Execution
  useEffect(() => {
    if (!mapInstance || isMapLoading) return;

    // Flush older HTML markers out safely
    markersRef.current.forEach((m) => m.remove());
    markersRef.current = [];

    // Clear dynamic diversion vector source routing routes if they exist from a past run
    if (mapInstance.getLayer("tactical-diversion-layer")) {
      mapInstance.removeLayer("tactical-diversion-layer");
    }
    if (mapInstance.getSource("tactical-diversion-source")) {
      mapInstance.removeSource("tactical-diversion-source");
    }

    // A. Render Routing GeoJSON
    if (diversions && diversions.coordinates) {
      mapInstance.addSource("tactical-diversion-source", {
        type: "geojson",
        data: diversions,
      });

      mapInstance.addLayer({
        id: "tactical-diversion-layer",
        type: "line",
        source: "tactical-diversion-source",
        layout: {
          "line-join": "round",
          "line-cap": "round",
        },
        paint: {
          "line-color": "#3b82f6",
          "line-width": 5,
          "line-dasharray": [2, 1],
        },
      });

      // Recenter camera smoothly to capture the active routing plan bounds
      const firstCoord = diversions.coordinates[0];
      if (firstCoord) {
        mapInstance.flyTo({ center: firstCoord, zoom: 14, speed: 1.2 });
      }
    } else if (activeSurge && activeSurge.longitude) {
      // Fallback camera target focus directly onto the primary anomaly focal link point
      mapInstance.flyTo({
        center: [activeSurge.longitude, activeSurge.latitude],
        zoom: 14,
        speed: 1.0,
      });
    }

    // B. Plot Dynamic Barricades Blockades
    if (barricades && barricades.length > 0) {
      barricades.forEach((point) => {
        let lat, lng;
        if (Array.isArray(point)) {
          [lng, lat] = point;
        } else if (point.latitude && point.longitude) {
          lat = point.latitude;
          lng = point.longitude;
        } else if (point.lat && point.lng) {
          lat = point.lat;
          lng = point.lng;
        }

        if (!lat || !lng) return;

        const el = document.createElement("div");
        el.innerHTML = renderToStaticMarkup(
          <div className="relative flex items-center justify-center group cursor-pointer">
            <div className="absolute inset-0 bg-yellow-500/50 blur-md rounded-full animate-pulse"></div>
            <div className="relative bg-gray-950 border border-yellow-500 text-yellow-500 px-2 py-1 rounded shadow-lg flex items-center gap-1 z-10">
              <ShieldAlert size={14} />
              <span className="text-[10px] font-mono font-bold whitespace-nowrap">
                CLOSED
              </span>
            </div>
          </div>,
        );

        const marker = new maplibregl.Marker({ element: el })
          .setLngLat([lng, lat])
          .addTo(mapInstance);
        markersRef.current.push(marker);
      });
    }
  }, [barricades, diversions, activeSurge, mapInstance, isMapLoading]);

  return (
    <div className="w-full h-full relative bg-gray-950 overflow-hidden">
      {isMapLoading && (
        <div className="absolute inset-0 z-50 flex flex-col items-center justify-center bg-gray-950/80 backdrop-blur-sm">
          <Loader2 className="w-8 h-8 text-blue-500 animate-spin mb-3" />
          <h3 className="text-sm font-mono tracking-wider text-gray-400">
            CONNECTING VECTOR RADAR GRID...
          </h3>
        </div>
      )}
      {isProcessing && (
        <div className="absolute top-4 left-4 z-10 bg-gray-900/90 border border-blue-500/40 text-blue-400 px-4 py-2 rounded font-mono text-xs shadow-xl flex items-center gap-2 backdrop-blur-md">
          <Loader2 size={14} className="animate-spin" />
          <span>RUNNING CELERY DISTRIBUTED OPERATIONS ANALYSIS...</span>
        </div>
      )}
      <div ref={mapContainerRef} className="w-full h-full" />
    </div>
  );
}

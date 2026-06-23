import React, { useState, useEffect, useRef } from "react";
import maplibregl from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css"; // Required for map rendering
import { renderToStaticMarkup } from "react-dom/server";
import { useSystemStore } from "../store/useSystemStore";
import { ShieldAlert, AlertTriangle, Loader2 } from "lucide-react";

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

  // Track HTML markers to clear them on re-renders
  const markersRef = useRef([]);

  // 1. Fetch backend metrics
  useEffect(() => {
    const fetchMetrics = async () => {
      try {
        let rawUrl =
          import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";
        if (!rawUrl.startsWith("http://") && !rawUrl.startsWith("https://")) {
          rawUrl = `https://${rawUrl}`;
        }
        const res = await fetch(`${rawUrl}/api/routing/network/metrics`);
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

  // 2. Initialize MapLibre (ZERO API KEYS REQUIRED)
  useEffect(() => {
    if (!mapContainerRef.current) return;

    const map = new maplibregl.Map({
      container: mapContainerRef.current,
      // Completely free, open-source dark mode map from CartoDB
      style: "https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json",
      center: [77.5946, 12.9716], // [longitude, latitude]
      zoom: 12.5,
      pitch: 45,
      attributionControl: false,
    });

    map.on("load", () => {
      setMapInstance(map);
      setIsMapLoading(false);
    });

    return () => map.remove();
  }, []);

  // 3. Cinematic Camera Sweeps
  useEffect(() => {
    if (activeSurge && mapInstance && !isMapLoading) {
      mapInstance.flyTo({
        center: [
          activeSurge.longitude || 77.5383,
          activeSurge.latitude || 12.9562,
        ],
        zoom: 15.5,
        pitch: 60,
        bearing: 25,
        duration: 2500,
      });
    }
  }, [activeSurge, mapInstance, isMapLoading]);

  // 4. Draw GeoJSON Layers (Native WebGL)
  useEffect(() => {
    if (!mapInstance || isMapLoading) return;

    // --- ROAD HEATMAP ---
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
            "line-width": ["interpolate", ["linear"], ["zoom"], 10, 3, 15, 8],
            // FIX 1: Add line-blur to create the "Weather Radar" melting effect
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

        // FIX 2: Add interactive popups to view exact ML Metrics
        mapInstance.on("click", "thermal-heat-layer", (e) => {
          if (!e.features || e.features.length === 0) return;
          const properties = e.features[0].properties;

          new maplibregl.Popup({ closeButton: true, closeOnClick: true })
            .setLngLat(e.lngLat)
            .setHTML(
              `
              <div class="p-2 bg-gray-900 border border-gray-700 rounded font-mono text-xs text-gray-100 shadow-xl">
                <strong class="text-blue-400 block mb-1">CORRIDOR:</strong> 
                <span class="uppercase">${properties.corridor || "Unknown"}</span>
                <div class="w-full h-px bg-gray-700 my-2"></div>
                <strong class="text-red-400 block mb-1">AI RISK SCORE:</strong> 
                <span class="text-lg">${properties.risk_score ? properties.risk_score.toFixed(2) : "N/A"}</span>
              </div>
            `,
            )
            .addTo(mapInstance);
        });

        // Change cursor to indicate the heatmap is clickable
        mapInstance.on("mouseenter", "thermal-heat-layer", () => {
          mapInstance.getCanvas().style.cursor = "pointer";
        });
        mapInstance.on("mouseleave", "thermal-heat-layer", () => {
          mapInstance.getCanvas().style.cursor = "";
        });
      }
    }

    // --- AI DIVERSION ROUTE ---
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

    // --- SURGE HEATMAP ---
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
              20,
              15,
              80,
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

  // 5. Draw HTML Markers (Barricades & Surge Pin)
  useEffect(() => {
    if (!mapInstance || isMapLoading) return;

    // Clear existing markers
    markersRef.current.forEach((marker) => marker.remove());
    markersRef.current = [];

    // --- SURGE PIN ---
    if (activeSurge && activeSurge.status !== "resolved") {
      const el = document.createElement("div");
      el.innerHTML = renderToStaticMarkup(
        <div className="relative flex items-center justify-center">
          <div className="absolute w-16 h-16 bg-red-600/30 rounded-full animate-ping"></div>
          <div className="bg-red-950 border-2 border-red-500 p-2 rounded-full shadow-[0_0_30px_rgba(239,68,68,1)] z-10">
            <AlertTriangle className="text-red-500" size={24} />
          </div>
        </div>,
      );

      const surgeMarker = new maplibregl.Marker({ element: el })
        .setLngLat([
          activeSurge.longitude || 77.5383,
          activeSurge.latitude || 12.9562,
        ])
        .addTo(mapInstance);
      markersRef.current.push(surgeMarker);
    }

    // --- BARRICADES ---
    if (barricades && barricades.length > 0) {
      barricades.forEach((coord) => {
        const lng = coord.lon !== undefined ? coord.lon : coord[0];
        const lat = coord.lat !== undefined ? coord.lat : coord[1];

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
  }, [barricades, activeSurge, mapInstance, isMapLoading]);

  return (
    <div className="w-full h-full relative bg-gray-950 overflow-hidden">
      {isMapLoading && (
        <div className="absolute inset-0 z-50 flex flex-col items-center justify-center bg-gray-950/80 backdrop-blur-sm">
          <Loader2 className="w-8 h-8 text-blue-500 animate-spin mb-3" />
          <h3 className="text-gray-300 font-mono text-sm tracking-widest font-bold">
            INITIALIZING TACTICAL MAP...
          </h3>
        </div>
      )}
      <div ref={mapContainerRef} className="absolute inset-0 w-full h-full" />
    </div>
  );
}

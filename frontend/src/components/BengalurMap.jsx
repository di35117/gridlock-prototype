import React, { useState, useEffect, useRef } from "react";
import maplibregl from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import { useSystemStore } from "../store/useSystemStore";
import { SAFE_API_URL } from "../services/websocket";
import { Loader2 } from "lucide-react";

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

  // 1. Initial Data Fetch for Road Metrics (Heatmap Data)
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

  // 2. Instantiate Map & Base Layers
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
      // A. Setup Base Heatmap Layer (Restored!)
      map.addSource("heatmap-source", {
        type: "geojson",
        data: { type: "FeatureCollection", features: [] }, // Injects data dynamically later
      });
      map.addLayer({
        id: "risk-heatmap-layer",
        type: "heatmap",
        source: "heatmap-source",
        maxzoom: 15,
        paint: {
          "heatmap-weight": 1,
          "heatmap-intensity": [
            "interpolate",
            ["linear"],
            ["zoom"],
            0,
            1,
            15,
            3,
          ],
          "heatmap-color": [
            "interpolate",
            ["linear"],
            ["heatmap-density"],
            0,
            "rgba(33,102,172,0)",
            0.2,
            "rgb(103,169,207)",
            0.4,
            "rgb(209,229,240)",
            0.6,
            "rgb(253,219,199)",
            0.8,
            "rgb(239,138,98)",
            1,
            "rgb(178,24,43)",
          ],
          "heatmap-radius": ["interpolate", ["linear"], ["zoom"], 0, 2, 15, 20],
          "heatmap-opacity": 0.7,
        },
      });

      // B. Setup Diversion Routing Line Layer
      map.addSource("tactical-diversion-source", {
        type: "geojson",
        data: { type: "FeatureCollection", features: [] },
      });
      map.addLayer({
        id: "tactical-diversion-layer",
        type: "line",
        source: "tactical-diversion-source",
        layout: { "line-join": "round", "line-cap": "round" },
        paint: {
          "line-color": "#3b82f6",
          "line-width": 5,
          "line-dasharray": [2, 1],
        },
      });

      // C. Setup GPU-Optimized Barricades Layer
      map.addSource("barricades-source", {
        type: "geojson",
        data: { type: "FeatureCollection", features: [] },
      });
      map.addLayer({
        id: "barricades-layer",
        type: "circle",
        source: "barricades-source",
        paint: {
          "circle-radius": 8,
          "circle-color": "#eab308",
          "circle-stroke-width": 2,
          "circle-stroke-color": "#030712",
        },
      });

      setIsMapLoading(false);
      setMapInstance(map);
    });

    return () => map.remove();
  }, []);

  // 3. Update Heatmap when roadMetrics state changes
  useEffect(() => {
    if (!mapInstance || !roadMetrics || isMapLoading) return;
    const source = mapInstance.getSource("heatmap-source");
    if (source) {
      source.setData(roadMetrics);
    }
  }, [roadMetrics, mapInstance, isMapLoading]);

  // 4. Update Tactical Routing & Barricades when Copilot finishes
  useEffect(() => {
    if (!mapInstance || isMapLoading) return;

    // Tactical Diversion Update
    const diversionSource = mapInstance.getSource("tactical-diversion-source");
    if (diversionSource) {
      if (diversions && diversions.coordinates) {
        diversionSource.setData(diversions);
        const firstCoord = diversions.coordinates[0];
        if (firstCoord) {
          mapInstance.flyTo({ center: firstCoord, zoom: 14, speed: 1.0 });
        }
      } else {
        diversionSource.setData({ type: "FeatureCollection", features: [] });
        if (activeSurge && activeSurge.longitude) {
          mapInstance.flyTo({
            center: [activeSurge.longitude, activeSurge.latitude],
            zoom: 14,
            speed: 1.0,
          });
        }
      }
    }

    // Barricades Layer Update
    const barricadesSource = mapInstance.getSource("barricades-source");
    if (barricadesSource) {
      if (barricades && barricades.length > 0) {
        const features = barricades
          .map((point) => {
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

            return {
              type: "Feature",
              geometry: { type: "Point", coordinates: [lng, lat] },
              properties: {},
            };
          })
          .filter(
            (f) => f.geometry.coordinates[0] && f.geometry.coordinates[1],
          );

        barricadesSource.setData({
          type: "FeatureCollection",
          features: features,
        });
      } else {
        barricadesSource.setData({ type: "FeatureCollection", features: [] });
      }
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

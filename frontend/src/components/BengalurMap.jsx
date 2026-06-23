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

  // 1. Initial Data Fetch for Road Metrics
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
      // A. Setup Base Road Metrics Layer (The Glowing ML Heatmap)
      map.addSource("heatmap-source", {
        type: "geojson",
        data: { type: "FeatureCollection", features: [] },
      });

      map.addLayer({
        id: "road-metrics-layer",
        type: "line",
        source: "heatmap-source",
        layout: {
          "line-join": "round",
          "line-cap": "round",
        },
        paint: {
          // Adjust "risk_score" if your backend uses a different metric name!
          "line-color": [
            "interpolate",
            ["linear"],
            ["get", "risk_score"],
            0,
            "rgba(255, 235, 59, 0.1)", // Faint transparent yellow
            50,
            "rgba(255, 152, 0, 0.6)", // Glowing orange
            100,
            "rgba(244, 67, 54, 0.9)", // Intense red
          ],
          "line-width": ["interpolate", ["linear"], ["zoom"], 10, 3, 15, 8],
          "line-blur": 4,
          "line-opacity": 0.85,
        },
      });

      // B. Setup Tactical Diversion Routing Line Layer
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

      // ==========================================
      // INTERACTIVITY: Click to reveal ML Metrics
      // ==========================================

      // Change cursor to pointer when hovering over a recorded road
      map.on("mouseenter", "road-metrics-layer", () => {
        map.getCanvas().style.cursor = "pointer";
      });
      map.on("mouseleave", "road-metrics-layer", () => {
        map.getCanvas().style.cursor = "";
      });

      // Click event handler
      map.on("click", "road-metrics-layer", (e) => {
        const feature = e.features[0];
        if (!feature || !feature.properties) return;

        const props = feature.properties;
        const corridor = props.corridor || props.name || "Unknown Link";

        // Parse numericals safely (Adjust property keys based on what your backend sends)
        const riskScore = props.risk_score
          ? Number(props.risk_score).toFixed(1)
          : "N/A";
        const riskColor =
          riskScore > 75
            ? "text-red-400"
            : riskScore > 40
              ? "text-orange-400"
              : "text-green-400";

        // Build a raw HTML string styled with Tailwind classes for the MapLibre Popup
        const popupHtml = `
          <div style="background-color: #111827; padding: 12px; border-radius: 6px; border: 1px solid #374151; min-width: 180px;">
            <h4 style="color: #60A5FA; font-family: monospace; font-weight: bold; margin-bottom: 8px; border-bottom: 1px solid #374151; padding-bottom: 4px; font-size: 12px; text-transform: uppercase;">
              ${corridor}
            </h4>
            <div style="display: grid; grid-template-columns: 1fr auto; gap: 6px; font-family: monospace; font-size: 11px;">
              <span style="color: #9CA3AF;">Risk Score:</span>
              <span class="${riskColor}" style="font-weight: bold; text-align: right;">${riskScore}</span>
              
              <span style="color: #9CA3AF;">Congestion:</span>
              <span style="color: #D1D5DB; text-align: right;">${props.congestion_level || props.congestion || "Normal"}</span>
              
              <span style="color: #9CA3AF;">ML Weight:</span>
              <span style="color: #D1D5DB; text-align: right;">${props.weight ? Number(props.weight).toFixed(2) : "1.00"}</span>
            </div>
          </div>
        `;

        new maplibregl.Popup({ closeButton: false, className: "cyber-popup" })
          .setLngLat(e.lngLat)
          .setHTML(popupHtml)
          .addTo(map);
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
      {/* Optional CSS snippet to remove the ugly white background from default MapLibre popups.
        Because MapLibre mounts popups directly to the DOM body, we have to use global CSS overrides here.
      */}
      <style>{`
        .cyber-popup .maplibregl-popup-content {
          background: transparent !important;
          padding: 0 !important;
          box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.5), 0 4px 6px -2px rgba(0, 0, 0, 0.3) !important;
        }
        .cyber-popup .maplibregl-popup-tip {
          border-top-color: #374151 !important; /* Matches our popup border */
        }
      `}</style>

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

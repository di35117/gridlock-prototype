'use client';
import React, { useState } from 'react';
import { Route, MapPin, Construction, ShieldAlert, Navigation, AlertTriangle, Layers } from 'lucide-react';

interface BarricadePoint {
  lat: number;
  lon: number;
}

interface RoutingResponse {
  status: string;
  route_geojson: any; 
  barricade_points: BarricadePoint[];
  blocked_construction_nodes: number;
}

export default function TacticalRoutingEngine() {
  const [isCalculating, setIsCalculating] = useState(false);
  const [routingData] = useState<RoutingResponse | null>({
    status: "Optimal Diversion Found",
    route_geojson: { type: "Feature" },
    blocked_construction_nodes: 14,
    barricade_points: [
      { lat: 12.9352, lon: 77.5341 },
      { lat: 12.9360, lon: 77.5348 },
      { lat: 12.9345, lon: 77.5332 },
    ]
  });

  const triggerReroute = () => {
    setIsCalculating(true);
    setTimeout(() => setIsCalculating(false), 1200);
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-50 p-6 font-sans">
      <header className="flex justify-between items-center mb-8 border-b border-slate-800 pb-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight flex items-center gap-2">
            <Route className="text-emerald-500" />
            Tactical Diversion Engine
          </h1>
          <p className="text-slate-400 text-sm mt-1">OSMnx Spatial Graph Pathfinding</p>
        </div>
        <div className="flex items-center gap-2 px-3 py-1.5 bg-emerald-500/10 text-emerald-400 rounded border border-emerald-500/20 text-sm font-mono">
          <Layers size={14} />
          <span>Graph Cache: Loaded (50MB)</span>
        </div>
      </header>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 h-[700px]">
        <div className="lg:col-span-4 flex flex-col gap-6 h-full">
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-6">
            <h2 className="text-lg font-semibold flex items-center gap-2 mb-4">
              <Navigation size={18} className="text-slate-400" />
              Route Parameters
            </h2>
            <div className="space-y-4 relative">
              <div className="absolute left-3.5 top-8 bottom-8 w-0.5 bg-slate-800 z-0"></div>
              <div className="relative z-10">
                <label className="block text-xs font-semibold text-slate-500 uppercase tracking-wider mb-1">Origin Point</label>
                <div className="flex items-center gap-3">
                  <div className="w-8 h-8 rounded-full bg-slate-800 border-2 border-slate-950 flex items-center justify-center text-blue-400">A</div>
                  <input type="text" defaultValue="12.9352, 77.5341" className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-sm text-slate-300 font-mono outline-none focus:border-emerald-500" />
                </div>
              </div>
              <div className="relative z-10">
                <label className="block text-xs font-semibold text-slate-500 uppercase tracking-wider mb-1">Destination</label>
                <div className="flex items-center gap-3">
                  <div className="w-8 h-8 rounded-full bg-slate-800 border-2 border-slate-950 flex items-center justify-center text-emerald-400">B</div>
                  <input type="text" defaultValue="12.9716, 77.5946" className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-sm text-slate-300 font-mono outline-none focus:border-emerald-500" />
                </div>
              </div>
            </div>
            <button 
              onClick={triggerReroute}
              disabled={isCalculating}
              className="w-full mt-6 bg-emerald-600 hover:bg-emerald-700 disabled:bg-slate-800 disabled:text-slate-500 text-white font-medium py-2.5 rounded-lg transition-colors flex justify-center items-center gap-2"
            >
              {isCalculating ? "Calculating Shortest Path..." : "Execute Spatial Reroute"}
            </button>
          </div>

          {routingData && (
            <div className="bg-slate-900 border border-slate-800 rounded-xl flex-1 flex flex-col overflow-hidden">
              <div className="p-4 border-b border-slate-800 bg-slate-900 flex justify-between items-center">
                <h3 className="font-semibold flex items-center gap-2">
                  <ShieldAlert size={16} className="text-amber-400" />
                  Barricade Deployments
                </h3>
                <span className="text-xs font-mono bg-slate-950 px-2 py-1 rounded text-slate-400 border border-slate-800">
                  {routingData.barricade_points.length} Nodes
                </span>
              </div>
              <div className="flex-1 overflow-y-auto p-2 space-y-2">
                {routingData.barricade_points.map((point, idx) => (
                  <div key={idx} className="flex items-center justify-between p-3 bg-slate-950 rounded-lg border border-slate-800/50 hover:border-amber-500/30 transition-colors">
                    <div className="flex items-center gap-3">
                      <div className="text-amber-500"><MapPin size={16} /></div>
                      <div>
                        <div className="text-xs font-mono text-slate-300">LAT: {point.lat.toFixed(4)}</div>
                        <div className="text-xs font-mono text-slate-300">LON: {point.lon.toFixed(4)}</div>
                      </div>
                    </div>
                    <button className="text-xs text-amber-500 hover:text-amber-400 font-medium px-2 py-1 bg-amber-500/10 rounded">
                      Dispatch
                    </button>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        <div className="lg:col-span-8 bg-slate-900 border border-slate-800 rounded-xl relative overflow-hidden flex flex-col">
          <div className="absolute top-4 left-4 right-4 z-10 flex gap-4">
            {routingData && (
              <>
                <div className={`px-4 py-3 rounded-lg shadow-lg border backdrop-blur-md flex items-center gap-3 ${
                  routingData.status.includes("Optimal") 
                    ? 'bg-emerald-950/80 border-emerald-500/30 text-emerald-400' 
                    : 'bg-rose-950/80 border-rose-500/30 text-rose-400'
                }`}>
                  {routingData.status.includes("Optimal") ? <Route size={20} /> : <AlertTriangle size={20} />}
                  <span className="font-semibold text-sm">{routingData.status}</span>
                </div>
                <div className="px-4 py-3 rounded-lg shadow-lg border border-slate-700/50 bg-slate-900/80 backdrop-blur-md flex items-center gap-3 text-slate-300 ml-auto">
                  <Construction size={18} className="text-amber-500" />
                  <span className="text-sm font-medium">Avoiding {routingData.blocked_construction_nodes} Graph Nodes</span>
                </div>
              </>
            )}
          </div>

          <div className="flex-1 bg-slate-950 flex flex-col items-center justify-center text-slate-600 relative">
             <div className="absolute inset-0 opacity-20" style={{ backgroundImage: 'radial-gradient(circle at 2px 2px, #334155 1px, transparent 0)', backgroundSize: '24px 24px' }}></div>
             <MapPin size={48} className="mb-4 opacity-50 text-slate-500" />
             <p className="font-mono text-sm">GeoJSON Render Target</p>
             <p className="text-xs mt-2 w-64 text-center">
               Mount your MapboxGL component here and pass `routingData.route_geojson` into the map source.
             </p>
          </div>
        </div>
      </div>
    </div>
  );
}
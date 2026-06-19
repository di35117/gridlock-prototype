'use client';
import React, { useState, useEffect } from 'react';
import { AlertTriangle, Users, Shield, Map, Activity, Calendar } from 'lucide-react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';

interface EventForecast {
  time: string;
  congestionLevel: number;
  baselineTraffic: number;
}

interface ResourcePlan {
  manpower: number;
  barricades: number;
  diversionRoutes: string[];
}

export default function CongestionCommandCenter() {
  const [forecastData, setForecastData] = useState<EventForecast[]>([]);
  const [resources, setResources] = useState<ResourcePlan | null>(null);

  useEffect(() => {
    setForecastData([
      { time: '14:00', congestionLevel: 45, baselineTraffic: 40 },
      { time: '15:00', congestionLevel: 65, baselineTraffic: 42 },
      { time: '16:00', congestionLevel: 92, baselineTraffic: 50 },
      { time: '17:00', congestionLevel: 88, baselineTraffic: 55 },
      { time: '18:00', congestionLevel: 60, baselineTraffic: 45 },
    ]);
    
    setResources({
      manpower: 24,
      barricades: 150,
      diversionRoutes: ['Route Alpha (via Ring Road)', 'Route Gamma (Heavy Vehicles)']
    });
  }, []);

  return (
    <div className="min-h-screen bg-slate-950 text-slate-50 p-6 font-sans">
      <header className="flex justify-between items-center mb-8 border-b border-slate-800 pb-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Traffic Ops Command</h1>
          <p className="text-slate-400 text-sm mt-1">Event-Driven Congestion Intelligence</p>
        </div>
        <div className="flex items-center gap-3 px-4 py-2 bg-rose-500/10 text-rose-400 rounded-md border border-rose-500/20">
          <AlertTriangle size={18} />
          <span className="text-sm font-semibold">Active Alert: City Marathon (Sector 4)</span>
        </div>
      </header>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 space-y-6">
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-6">
            <div className="flex justify-between items-center mb-6">
              <h2 className="text-lg font-semibold flex items-center gap-2">
                <Activity size={20} className="text-blue-400" />
                Impact Forecast (Next 6 Hours)
              </h2>
            </div>
            <div className="h-72 w-full">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={forecastData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" vertical={false} />
                  <XAxis dataKey="time" stroke="#64748b" fontSize={12} tickLine={false} />
                  <YAxis stroke="#64748b" fontSize={12} tickLine={false} axisLine={false} />
                  <Tooltip 
                    contentStyle={{ backgroundColor: '#0f172a', borderColor: '#1e293b', borderRadius: '8px' }}
                    itemStyle={{ color: '#e2e8f0' }}
                  />
                  <Line type="monotone" dataKey="congestionLevel" stroke="#ef4444" strokeWidth={3} dot={{ r: 4 }} name="Predicted Impact" />
                  <Line type="monotone" dataKey="baselineTraffic" stroke="#3b82f6" strokeWidth={2} strokeDasharray="5 5" name="Normal Baseline" />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </div>

          <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 h-80 flex flex-col">
            <h2 className="text-lg font-semibold flex items-center gap-2 mb-4">
              <Map size={20} className="text-emerald-400" />
              Live Diversion Routing
            </h2>
            <div className="flex-1 bg-slate-800/50 rounded-lg border border-slate-700 flex items-center justify-center">
              <p className="text-slate-500 text-sm">Interactive Map Integration Area</p>
            </div>
          </div>
        </div>

        <div className="space-y-6">
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-6">
             <h2 className="text-lg font-semibold mb-6 flex items-center gap-2">
                <Calendar size={20} className="text-purple-400" />
                Optimal Resource Plan
             </h2>
             
             <div className="grid grid-cols-2 gap-4 mb-6">
               <div className="bg-slate-950 p-4 rounded-lg border border-slate-800">
                 <div className="flex items-center gap-2 text-slate-400 mb-2">
                   <Users size={16} />
                   <span className="text-xs uppercase tracking-wider font-semibold">Personnel</span>
                 </div>
                 <div className="text-3xl font-bold text-white">{resources?.manpower}</div>
                 <div className="text-xs text-emerald-400 mt-1">+12 from standard</div>
               </div>
               <div className="bg-slate-950 p-4 rounded-lg border border-slate-800">
                 <div className="flex items-center gap-2 text-slate-400 mb-2">
                   <Shield size={16} />
                   <span className="text-xs uppercase tracking-wider font-semibold">Barricades</span>
                 </div>
                 <div className="text-3xl font-bold text-white">{resources?.barricades}</div>
                 <div className="text-xs text-emerald-400 mt-1">Deploy at 3 junctions</div>
               </div>
             </div>

             <div>
               <h3 className="text-sm font-semibold text-slate-400 mb-3 uppercase tracking-wider">Recommended Diversions</h3>
               <ul className="space-y-3">
                 {resources?.diversionRoutes.map((route, idx) => (
                   <li key={idx} className="flex items-start gap-3 p-3 bg-slate-800/30 rounded-md border border-slate-800/50">
                     <div className="mt-0.5 w-2 h-2 rounded-full bg-blue-500"></div>
                     <span className="text-sm text-slate-200">{route}</span>
                   </li>
                 ))}
               </ul>
             </div>

             <button className="w-full mt-6 bg-blue-600 hover:bg-blue-700 text-white font-medium py-2.5 rounded-lg transition-colors">
               Dispatch Resources
             </button>
          </div>
        </div>
      </div>
    </div>
  );
}
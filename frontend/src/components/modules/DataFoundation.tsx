'use client';
import React, { useState } from 'react';
import { Database, ShieldAlert, BarChart3, RefreshCw, Server, MapPin } from 'lucide-react';

interface SystemStatus {
  status: string;
  record_counts: {
    incidents: number;
    corridor_risk_profiles: number;
    station_corridor_mapping: number;
    event_cause_stats: number;
  };
}

interface CorridorProfile {
  corridor: string;
  total_incidents: number;
  closure_rate: number;
  high_priority_rate: number;
  risk_score: number;
  avg_hourly_baseline: number;
}

export default function DataFoundationHub() {
  const [isReloading, setIsReloading] = useState(false);
  
  const [sysStatus] = useState<SystemStatus>({
    status: "ok",
    record_counts: {
      incidents: 8173,
      corridor_risk_profiles: 142,
      station_corridor_mapping: 142,
      event_cause_stats: 6
    }
  });

  const [profiles] = useState<CorridorProfile[]>([
    { corridor: "Outer Ring Road (Bellandur)", total_incidents: 412, closure_rate: 0.32, high_priority_rate: 0.45, risk_score: 8.7, avg_hourly_baseline: 4.2 },
    { corridor: "Hosur Road (Silk Board)", total_incidents: 389, closure_rate: 0.15, high_priority_rate: 0.51, risk_score: 7.9, avg_hourly_baseline: 3.8 },
    { corridor: "Tumkur Road (Goraguntepalya)", total_incidents: 275, closure_rate: 0.28, high_priority_rate: 0.30, risk_score: 6.4, avg_hourly_baseline: 2.1 },
    { corridor: "Old Madras Road (KR Puram)", total_incidents: 210, closure_rate: 0.10, high_priority_rate: 0.22, risk_score: 4.2, avg_hourly_baseline: 1.5 },
  ]);

  const handleReload = () => {
    setIsReloading(true);
    setTimeout(() => setIsReloading(false), 2000); 
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-50 p-6 font-sans">
      <header className="flex justify-between items-center mb-8 border-b border-slate-800 pb-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight flex items-center gap-2">
            <Database className="text-indigo-500" />
            ASTRAM Data Foundation
          </h1>
          <p className="text-slate-400 text-sm mt-1">Pre-computed historical risk profiles and telemetry DNA</p>
        </div>
        <button 
          onClick={handleReload}
          className="flex items-center gap-2 px-4 py-2 bg-slate-900 hover:bg-slate-800 border border-slate-700 rounded-md transition-all text-sm font-medium"
        >
          <RefreshCw size={16} className={isReloading ? "animate-spin text-indigo-400" : "text-slate-400"} />
          {isReloading ? "Rebuilding DNA..." : "Force CSV Reload"}
        </button>
      </header>

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        {[
          { label: "Raw Incidents Indexed", val: sysStatus.record_counts.incidents.toLocaleString(), icon: Server, color: "text-blue-400" },
          { label: "Corridor Profiles", val: sysStatus.record_counts.corridor_risk_profiles, icon: MapPin, color: "text-emerald-400" },
          { label: "Station Mappings", val: sysStatus.record_counts.station_corridor_mapping, icon: ShieldAlert, color: "text-amber-400" },
          { label: "Severity Models", val: sysStatus.record_counts.event_cause_stats, icon: BarChart3, color: "text-purple-400" },
        ].map((stat, idx) => (
          <div key={idx} className="bg-slate-900 border border-slate-800 rounded-xl p-5 flex items-center gap-4">
            <div className={`p-3 bg-slate-950 rounded-lg border border-slate-800 ${stat.color}`}>
              <stat.icon size={20} />
            </div>
            <div>
              <div className="text-2xl font-bold text-slate-100">{stat.val}</div>
              <div className="text-xs uppercase tracking-wider text-slate-500 font-semibold mt-0.5">{stat.label}</div>
            </div>
          </div>
        ))}
      </div>

      <div className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden">
        <div className="px-6 py-5 border-b border-slate-800 flex justify-between items-center bg-slate-900/50">
          <h2 className="text-lg font-semibold">High-Risk Corridor Matrix</h2>
          <span className="text-xs font-mono text-slate-400 bg-slate-950 px-2 py-1 rounded border border-slate-800">
            SORT: risk_score DESC
          </span>
        </div>
        
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead className="bg-slate-950 text-slate-400 border-b border-slate-800">
              <tr>
                <th className="px-6 py-4 font-semibold">Corridor Location</th>
                <th className="px-6 py-4 font-semibold">Historical Incidents</th>
                <th className="px-6 py-4 font-semibold">Closure Probability</th>
                <th className="px-6 py-4 font-semibold">Avg Hourly Surge</th>
                <th className="px-6 py-4 font-semibold">Composite Risk Score</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/50">
              {profiles.map((profile, idx) => (
                <tr key={idx} className="hover:bg-slate-800/20 transition-colors">
                  <td className="px-6 py-4 font-medium text-slate-200">{profile.corridor}</td>
                  <td className="px-6 py-4 text-slate-300">{profile.total_incidents}</td>
                  <td className="px-6 py-4">
                    <span className={`px-2.5 py-1 rounded-full text-xs font-medium border ${
                      profile.closure_rate > 0.25 ? 'bg-rose-500/10 text-rose-400 border-rose-500/20' : 'bg-amber-500/10 text-amber-400 border-amber-500/20'
                    }`}>
                      {(profile.closure_rate * 100).toFixed(1)}%
                    </span>
                  </td>
                  <td className="px-6 py-4 text-slate-300 font-mono">{profile.avg_hourly_baseline} / hr</td>
                  <td className="px-6 py-4 w-64">
                    <div className="flex items-center gap-3">
                      <span className="font-bold text-slate-200 w-8">{profile.risk_score}</span>
                      <div className="h-2 flex-1 bg-slate-950 rounded-full overflow-hidden border border-slate-800">
                        <div 
                          className={`h-full rounded-full ${
                            profile.risk_score > 8 ? 'bg-rose-500' : profile.risk_score > 6 ? 'bg-amber-500' : 'bg-emerald-500'
                          }`}
                          style={{ width: `${(profile.risk_score / 10) * 100}%` }}
                        />
                      </div>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
'use client';
import React, { useState } from 'react';
import { Users, Shield, Target, AlertTriangle, CheckCircle2, TrendingUp, BarChart } from 'lucide-react';

interface TacticalResponse {
  primary_stations: string[];
  manpower_tier: string;
  recommended_barricade_count: number;
}

interface OptimizeResponse {
  allocations: Record<string, number>;
  unmet_demand: number;
  optimization_status: string;
}

export default function ResourceRecommender() {
  const [totalOfficers, setTotalOfficers] = useState(150);
  const [isOptimizing, setIsOptimizing] = useState(false);

  const [tacticalPlan] = useState<TacticalResponse>({
    primary_stations: ["Indiranagar PS", "Jeevan Bima Nagar PS"],
    manpower_tier: "Tier 1 (Major Deployment)",
    recommended_barricade_count: 40
  });

  const [optResult, setOptResult] = useState<OptimizeResponse | null>({
    allocations: {
      "Mysore Rd Protest": 80,
      "ORR Construction Surge": 50,
      "MG Road VIP": 20
    },
    unmet_demand: 30,
    optimization_status: "Optimal"
  });

  const runOptimization = () => {
    setIsOptimizing(true);
    setTimeout(() => setIsOptimizing(false), 800);
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-50 p-6 font-sans">
      <header className="flex justify-between items-center mb-8 border-b border-slate-800 pb-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight flex items-center gap-2">
            <Target className="text-rose-500" />
            Resource Operations Command
          </h1>
          <p className="text-slate-400 text-sm mt-1">PuLP Linear Programming & Prescriptive Allocation</p>
        </div>
        <div className="flex items-center gap-2 px-3 py-1.5 bg-rose-500/10 text-rose-400 rounded border border-rose-500/20 text-sm font-mono">
          <TrendingUp size={14} />
          <span>Objective: Maximize Risk-Weighted Deployment</span>
        </div>
      </header>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        <div className="lg:col-span-4 space-y-6">
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-6">
            <h2 className="text-lg font-semibold mb-6 flex items-center gap-2">
              <Shield size={18} className="text-slate-400" />
              Tactical Playbook
            </h2>
            <div className="space-y-6">
              <div>
                <div className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-2">Primary Responding Stations</div>
                <div className="flex flex-wrap gap-2">
                  {tacticalPlan.primary_stations.map((station, idx) => (
                    <span key={idx} className="bg-slate-950 border border-slate-800 text-slate-300 px-3 py-1.5 rounded-md text-sm">
                      {station}
                    </span>
                  ))}
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div className="bg-slate-950 border border-slate-800 p-4 rounded-lg">
                  <div className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-1">Mobilization</div>
                  <div className="font-bold text-rose-400">{tacticalPlan.manpower_tier}</div>
                </div>
                <div className="bg-slate-950 border border-slate-800 p-4 rounded-lg">
                  <div className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-1">Barricades</div>
                  <div className="text-2xl font-bold text-white">{tacticalPlan.recommended_barricade_count}</div>
                  <div className="text-xs text-slate-500 mt-1">Recommended</div>
                </div>
              </div>
            </div>
          </div>
        </div>

        <div className="lg:col-span-8 space-y-6">
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-6">
            <div className="flex justify-between items-start mb-6">
              <div>
                <h2 className="text-lg font-semibold flex items-center gap-2">
                  <BarChart size={18} className="text-emerald-400" />
                  Fleet Optimization Matrix
                </h2>
                <p className="text-sm text-slate-400 mt-1">Solves for optimal distribution of limited personnel across concurrent high-risk events.</p>
              </div>
              <div className="flex items-center gap-4">
                <div className="text-right">
                  <div className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Total Shift Roster</div>
                  <input 
                    type="number" 
                    value={totalOfficers}
                    onChange={(e) => setTotalOfficers(Number(e.target.value))}
                    className="bg-slate-950 border border-slate-800 rounded px-3 py-1 mt-1 text-emerald-400 font-bold w-24 text-right outline-none focus:border-emerald-500"
                  />
                </div>
                <button 
                  onClick={runOptimization}
                  disabled={isOptimizing}
                  className="bg-emerald-600 hover:bg-emerald-700 text-white px-4 py-2 rounded-lg font-medium transition-colors disabled:opacity-50 mt-2"
                >
                  {isOptimizing ? "Solving LP..." : "Run PuLP Engine"}
                </button>
              </div>
            </div>

            {optResult && (
              <div className="animate-in fade-in duration-500 space-y-6">
                <div className="flex gap-4">
                  <div className="flex-1 bg-emerald-500/10 border border-emerald-500/20 p-3 rounded-lg flex items-center gap-3">
                    <CheckCircle2 className="text-emerald-500" />
                    <div>
                      <div className="text-xs text-emerald-500 uppercase font-semibold">Solver Status</div>
                      <div className="font-mono text-emerald-400">{optResult.optimization_status}</div>
                    </div>
                  </div>
                  <div className={`flex-1 border p-3 rounded-lg flex items-center gap-3 ${optResult.unmet_demand > 0 ? 'bg-rose-500/10 border-rose-500/20' : 'bg-slate-950 border-slate-800'}`}>
                    <AlertTriangle className={optResult.unmet_demand > 0 ? 'text-rose-500' : 'text-slate-500'} />
                    <div>
                      <div className={`text-xs uppercase font-semibold ${optResult.unmet_demand > 0 ? 'text-rose-500' : 'text-slate-500'}`}>System Deficit (Unmet Demand)</div>
                      <div className={`font-bold text-lg ${optResult.unmet_demand > 0 ? 'text-rose-400' : 'text-slate-400'}`}>{optResult.unmet_demand} Personnel</div>
                    </div>
                  </div>
                </div>

                <div className="space-y-4 border-t border-slate-800 pt-6">
                  <div className="text-sm font-semibold text-slate-300 uppercase tracking-wider mb-2">Deployment Orders</div>
                  {Object.entries(optResult.allocations).map(([event, count], idx) => {
                    const percentage = (count / totalOfficers) * 100;
                    return (
                      <div key={idx} className="bg-slate-950 p-4 rounded-lg border border-slate-800">
                        <div className="flex justify-between items-center mb-2">
                          <span className="font-medium text-slate-200">{event}</span>
                          <span className="font-mono text-emerald-400 font-bold">{count} Officers Assigned</span>
                        </div>
                        <div className="w-full h-2 bg-slate-900 rounded-full overflow-hidden">
                          <div 
                            className="h-full bg-emerald-500 rounded-full transition-all duration-1000"
                            style={{ width: `${percentage}%` }}
                          />
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
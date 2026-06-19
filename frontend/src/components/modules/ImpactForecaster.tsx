'use client';
import React, { useState } from 'react';
import { BrainCircuit, Activity, Clock, MapPin, Zap, Settings2 } from 'lucide-react';
import { AreaChart, Area, XAxis, Tooltip, ResponsiveContainer } from 'recharts';

interface ForecastRequest {
  event_cause: string;
  corridor: string;
  hour_of_day: number;
  day_of_week: number;
  veh_type: string;
}

interface ForecastResponse {
  priority_prediction: string;
  closure_probability: number;
  corridor_risk_score: number;
  compound_risk_score: number;
  risk_level: 'Low' | 'Medium' | 'High' | 'Critical';
}

export default function ImpactForecaster() {
  const [isTraining, setIsTraining] = useState(false);
  const [formData, setFormData] = useState<ForecastRequest>({
    event_cause: 'public_event',
    corridor: 'Outer Ring Road',
    hour_of_day: 14,
    day_of_week: 5,
    veh_type: 'unknown'
  });

  const [forecast] = useState<ForecastResponse | null>({
    priority_prediction: 'High',
    closure_probability: 0.68,
    corridor_risk_score: 7.2,
    compound_risk_score: 0.82,
    risk_level: 'Critical'
  });

  const handleRetrain = () => {
    setIsTraining(true);
    setTimeout(() => setIsTraining(false), 3000);
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-50 p-6 font-sans">
      <header className="flex justify-between items-center mb-8 border-b border-slate-800 pb-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight flex items-center gap-2">
            <BrainCircuit className="text-purple-500" />
            Predictive Impact Forecaster
          </h1>
          <p className="text-slate-400 text-sm mt-1">LightGBM Ensembled Threat Modeling</p>
        </div>
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2 px-3 py-1.5 bg-emerald-500/10 text-emerald-400 rounded border border-emerald-500/20 text-sm font-mono">
            <Activity size={14} />
            <span>Models Active (Tripwire: 0.50)</span>
          </div>
          <button 
            onClick={handleRetrain}
            disabled={isTraining}
            className="flex items-center gap-2 px-4 py-2 bg-slate-900 hover:bg-slate-800 border border-slate-700 rounded-md transition-all text-sm font-medium disabled:opacity-50"
          >
            <Settings2 size={16} className={isTraining ? "animate-spin" : ""} />
            {isTraining ? "Pipeline Running..." : "Retrain Models"}
          </button>
        </div>
      </header>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        <div className="lg:col-span-4 space-y-6">
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-6">
            <h2 className="text-lg font-semibold mb-5 flex items-center gap-2">
              <Settings2 size={18} className="text-slate-400" />
              Event Parameters
            </h2>
            <div className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-slate-500 uppercase tracking-wider mb-2">Event Cause</label>
                <select className="w-full bg-slate-950 border border-slate-800 rounded-lg px-4 py-2.5 text-sm focus:ring-2 focus:ring-purple-500 outline-none transition-all">
                  <option value="public_event">Public Event</option>
                  <option value="procession">Procession</option>
                  <option value="construction">Construction</option>
                  <option value="vip_movement">VIP Movement</option>
                </select>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-500 uppercase tracking-wider mb-2">Target Corridor</label>
                <div className="relative">
                  <MapPin size={16} className="absolute left-3 top-3 text-slate-500" />
                  <input type="text" defaultValue={formData.corridor} className="w-full bg-slate-950 border border-slate-800 rounded-lg pl-10 pr-4 py-2.5 text-sm focus:ring-2 focus:ring-purple-500 outline-none transition-all" />
                </div>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-500 uppercase tracking-wider mb-2 flex justify-between">
                  <span>Hour of Day</span>
                  <span className="text-purple-400 font-mono">{formData.hour_of_day}:00</span>
                </label>
                <input type="range" min="0" max="23" defaultValue={formData.hour_of_day} className="w-full accent-purple-500" />
              </div>
            </div>
          </div>
        </div>

        <div className="lg:col-span-8 space-y-6">
          <div className="grid grid-cols-3 gap-4">
            <div className="bg-slate-900 border border-slate-800 rounded-xl p-5">
              <div className="text-slate-500 text-xs font-semibold uppercase tracking-wider mb-1">Closure Probability</div>
              <div className="text-3xl font-bold text-slate-100 mb-2">{(forecast!.closure_probability * 100).toFixed(1)}%</div>
              <div className="w-full bg-slate-950 h-1.5 rounded-full overflow-hidden">
                <div className="bg-amber-500 h-full rounded-full" style={{ width: `${forecast!.closure_probability * 100}%` }}></div>
              </div>
            </div>
            
            <div className="bg-slate-900 border border-slate-800 rounded-xl p-5">
              <div className="text-slate-500 text-xs font-semibold uppercase tracking-wider mb-1">Priority Prediction</div>
              <div className="text-3xl font-bold text-rose-400 mb-2">{forecast?.priority_prediction}</div>
              <div className="text-xs text-slate-500 font-mono">Confidence: 89.4%</div>
            </div>

            <div className="bg-slate-900 border-2 border-purple-500/20 rounded-xl p-5 relative overflow-hidden">
              <div className="absolute top-0 right-0 p-4 opacity-10"><Zap size={48} /></div>
              <div className="text-purple-400 text-xs font-semibold uppercase tracking-wider mb-1">Compound Risk Level</div>
              <div className="text-3xl font-bold text-white mb-1">{forecast?.risk_level}</div>
              <div className="text-sm text-purple-300 font-mono">Score: {forecast?.compound_risk_score}</div>
            </div>
          </div>

          <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 h-64">
            <h3 className="text-sm font-semibold text-slate-400 mb-4 flex items-center gap-2">
              <Clock size={16} /> Risk Volatility Curve (24h Forecast)
            </h3>
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={[
                { hour: '08:00', risk: 0.2 }, { hour: '10:00', risk: 0.4 },
                { hour: '12:00', risk: 0.5 }, { hour: '14:00', risk: 0.82 },
                { hour: '16:00', risk: 0.9 }, { hour: '18:00', risk: 0.6 }
              ]}>
                <defs>
                  <linearGradient id="colorRisk" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#a855f7" stopOpacity={0.3}/>
                    <stop offset="95%" stopColor="#a855f7" stopOpacity={0}/>
                  </linearGradient>
                </defs>
                <XAxis dataKey="hour" stroke="#475569" fontSize={12} tickLine={false} />
                <Tooltip contentStyle={{ backgroundColor: '#0f172a', borderColor: '#1e293b' }} />
                <Area type="monotone" dataKey="risk" stroke="#a855f7" strokeWidth={2} fillOpacity={1} fill="url(#colorRisk)" />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>
    </div>
  );
}
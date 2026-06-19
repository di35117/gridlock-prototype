'use client';
import React, { useState } from 'react';
import { Activity, Radio, AlertTriangle, Zap, CheckCircle2, Waves } from 'lucide-react';

interface SurgeResponse {
  corridor: string;
  baseline_mean: number;
  baseline_std: number;
  current_incidents: number;
  z_score: number;
  is_surge_detected: boolean;
  automated_action: string | null;
}

export default function SurgeDetectorEngine() {
  const [isScanning, setIsScanning] = useState(false);
  const [lastScanTime, setLastScanTime] = useState<string>("Waiting for daemon...");
  const [surgeData, setSurgeData] = useState<SurgeResponse | null>(null);

  const simulateDaemonWakeup = () => {
    setIsScanning(true);
    setSurgeData(null);
    setTimeout(() => {
      const now = new Date();
      setLastScanTime(now.toLocaleTimeString());
      setSurgeData({
        corridor: "Mysore Road",
        baseline_mean: 12.5,
        baseline_std: 4.2,
        current_incidents: 85,
        z_score: 17.26,
        is_surge_detected: true,
        automated_action: "URGENT: Sudden gathering or severe bottleneck detected. Z-Score: 17.26. Immediate QR deployment recommended."
      });
      setIsScanning(false);
    }, 1500);
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-50 p-6 font-sans">
      <header className="flex justify-between items-center mb-8 border-b border-slate-800 pb-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight flex items-center gap-2">
            <Waves className="text-cyan-500" />
            Autonomous Surge Monitor
          </h1>
          <p className="text-slate-400 text-sm mt-1">Z-Score Anomaly Detection & Live Telemetry</p>
        </div>
        <div className="flex items-center gap-4">
          <div className="text-right">
            <div className="text-xs text-slate-500 uppercase font-semibold">Last Daemon Scan</div>
            <div className="text-sm font-mono text-slate-300">{lastScanTime}</div>
          </div>
          <button 
            onClick={simulateDaemonWakeup}
            disabled={isScanning}
            className="flex items-center gap-2 px-4 py-2 bg-slate-900 hover:bg-slate-800 border border-slate-700 rounded-md transition-all text-sm font-medium disabled:opacity-50"
          >
            <Radio size={16} className={isScanning ? "animate-pulse text-cyan-400" : "text-slate-400"} />
            {isScanning ? "Scanning Live ASTRAM..." : "Force Daemon Scan"}
          </button>
        </div>
      </header>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 h-[600px]">
        <div className="lg:col-span-4 bg-slate-900 border border-slate-800 rounded-xl p-6 flex flex-col items-center justify-center relative overflow-hidden">
          <div className="absolute top-4 left-4 flex items-center gap-2 text-xs font-mono text-slate-500 uppercase">
            <Activity size={14} /> Live Telemetry Feed
          </div>

          <div className="relative w-64 h-64 rounded-full border border-slate-800 flex items-center justify-center">
            <div className={`absolute inset-0 rounded-full border border-cyan-500/20 ${isScanning ? 'animate-ping' : ''}`}></div>
            <div className="absolute w-48 h-48 rounded-full border border-slate-800"></div>
            <div className="absolute w-32 h-32 rounded-full border border-slate-800"></div>
            
            {isScanning ? (
              <div className="text-cyan-400 animate-pulse flex flex-col items-center">
                <Radio size={32} className="mb-2" />
                <span className="text-xs font-mono tracking-widest uppercase">Polling Data</span>
              </div>
            ) : surgeData?.is_surge_detected ? (
              <div className="text-rose-500 animate-bounce flex flex-col items-center">
                <AlertTriangle size={48} className="mb-2" />
                <span className="text-xs font-bold tracking-widest uppercase">Anomaly</span>
              </div>
            ) : (
              <div className="text-slate-600 flex flex-col items-center">
                <CheckCircle2 size={32} className="mb-2" />
                <span className="text-xs font-mono tracking-widest uppercase">Standby</span>
              </div>
            )}
          </div>
        </div>

        <div className="lg:col-span-8 flex flex-col gap-6">
          {!surgeData ? (
            <div className="flex-1 bg-slate-900 border border-slate-800 rounded-xl flex items-center justify-center text-slate-500 font-mono text-sm">
              Waiting for next daemon interval to process telemetry...
            </div>
          ) : (
            <>
              {surgeData.is_surge_detected && (
                <div className="bg-rose-500/10 border-2 border-rose-500/30 rounded-xl p-5 animate-in fade-in slide-in-from-top-4">
                  <div className="flex items-start gap-4">
                    <div className="bg-rose-500/20 p-3 rounded-lg">
                      <Zap size={24} className="text-rose-500" />
                    </div>
                    <div>
                      <h3 className="text-lg font-bold text-rose-400 uppercase tracking-wider mb-1">
                        Surge WebSocket Broadcast
                      </h3>
                      <p className="text-rose-100 font-mono text-sm leading-relaxed">
                        {surgeData.automated_action}
                      </p>
                    </div>
                  </div>
                </div>
              )}

              <div className="flex-1 bg-slate-900 border border-slate-800 rounded-xl p-6 animate-in fade-in duration-500">
                <h2 className="text-lg font-semibold flex items-center gap-2 mb-6">
                  <Activity size={18} className="text-slate-400" />
                  Statistical Z-Score Analysis: {surgeData.corridor}
                </h2>

                <div className="grid grid-cols-3 gap-4 mb-8">
                  <div className="bg-slate-950 border border-slate-800 p-4 rounded-lg">
                    <div className="text-xs text-slate-500 uppercase font-semibold mb-1">Baseline Mean (μ)</div>
                    <div className="text-2xl font-mono text-slate-300">{surgeData.baseline_mean}</div>
                  </div>
                  <div className="bg-slate-950 border border-slate-800 p-4 rounded-lg">
                    <div className="text-xs text-slate-500 uppercase font-semibold mb-1">Standard Dev (σ)</div>
                    <div className="text-2xl font-mono text-slate-300">{surgeData.baseline_std}</div>
                  </div>
                  <div className="bg-slate-950 border border-slate-800 p-4 rounded-lg border-b-2 border-b-cyan-500">
                    <div className="text-xs text-cyan-500 uppercase font-bold mb-1">Current Incidents (X)</div>
                    <div className="text-2xl font-mono text-white">{surgeData.current_incidents}</div>
                  </div>
                </div>

                <div>
                  <div className="flex justify-between items-end mb-2">
                    <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Anomaly Threshold (2.0σ)</span>
                    <span className={`text-2xl font-bold font-mono ${surgeData.z_score > 2.0 ? 'text-rose-500' : 'text-emerald-400'}`}>
                      Z = {surgeData.z_score.toFixed(2)}
                    </span>
                  </div>
                  <div className="relative w-full h-4 bg-slate-950 rounded-full overflow-hidden border border-slate-800">
                    <div className="absolute top-0 bottom-0 left-[20%] w-0.5 bg-slate-500 z-10"></div>
                    <div 
                      className={`h-full transition-all duration-1000 ${surgeData.z_score > 2.0 ? 'bg-rose-500' : 'bg-emerald-500'}`}
                      style={{ width: `${Math.min((surgeData.z_score / 20) * 100, 100)}%` }}
                    ></div>
                  </div>
                  <div className="flex justify-between text-xs text-slate-500 mt-2 font-mono">
                    <span>0.0</span>
                    <span className="ml-[-10%]">2.0 (Trigger)</span>
                    <span>20.0+</span>
                  </div>
                </div>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
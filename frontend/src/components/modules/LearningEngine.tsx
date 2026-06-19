'use client';
import React, { useState } from 'react';
import { Network, Activity, Database, ChevronRight, Zap, RefreshCw, CheckCircle2 } from 'lucide-react';

interface ActiveEvent {
  event_id: string;
  corridor: string;
  event_cause: string;
  predicted_risk: number;
  expected_end_time: string;
}

interface LearningInsight {
  corridor: string;
  event_cause: string;
  predicted_severity: number;
  observed_severity: number;
  previous_calibration: number;
  new_calibration_factor: number;
  learning_insight: string;
}

export default function LearningEngineDashboard() {
  const [isPolling, setIsPolling] = useState(false);
  const [activeQueue] = useState<ActiveEvent[]>([
    { event_id: "CCTV-A1B2", corridor: "Outer Ring Road", event_cause: "water_logging", predicted_risk: 0.85, expected_end_time: "15:30:00" },
    { event_id: "MAN-9F8D", corridor: "Hosur Road", event_cause: "construction", predicted_risk: 0.60, expected_end_time: "16:45:00" }
  ]);
  const [latestInsight, setLatestInsight] = useState<LearningInsight | null>(null);

  const simulateDaemonPoll = (event: ActiveEvent) => {
    setIsPolling(true);
    setTimeout(() => {
      setLatestInsight({
        corridor: event.corridor,
        event_cause: event.event_cause,
        predicted_severity: event.predicted_risk,
        observed_severity: 1.4,
        previous_calibration: 1.0,
        new_calibration_factor: 1.15,
        learning_insight: `Model under-predicted. ${event.corridor} is highly vulnerable to ${event.event_cause}. Multiplier updated to 1.15x.`
      });
      setIsPolling(false);
    }, 1500);
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-50 p-6 font-sans">
      <header className="flex justify-between items-center mb-8 border-b border-slate-800 pb-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight flex items-center gap-2">
            <Network className="text-blue-500" />
            Autonomous Learning Engine
          </h1>
          <p className="text-slate-400 text-sm mt-1">EMA Calibration & Redis Daemon Monitor</p>
        </div>
        <div className="flex items-center gap-2 px-3 py-1.5 bg-blue-500/10 text-blue-400 rounded border border-blue-500/20 text-sm font-mono">
          <Database size={14} />
          <span>Redis Connection: Stable</span>
        </div>
      </header>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 flex flex-col h-[500px]">
          <div className="flex justify-between items-center mb-6">
            <h2 className="text-lg font-semibold flex items-center gap-2">
              <Activity size={18} className="text-slate-400" />
              Active Event Tracker (Daemon Queue)
            </h2>
            <span className="text-xs bg-slate-800 px-2 py-1 rounded text-slate-400 font-mono">
              {activeQueue.length} Active
            </span>
          </div>

          <div className="flex-1 overflow-y-auto space-y-3 pr-2">
            {activeQueue.map((ev, idx) => (
              <div key={idx} className="bg-slate-950 border border-slate-800 rounded-lg p-4 group hover:border-slate-600 transition-colors">
                <div className="flex justify-between items-start mb-3">
                  <div>
                    <div className="text-sm font-mono text-slate-400 mb-1">{ev.event_id}</div>
                    <div className="font-semibold text-slate-200">{ev.corridor}</div>
                  </div>
                  <div className="text-right">
                    <div className="text-xs uppercase tracking-wider text-slate-500 font-semibold mb-1">Closes At</div>
                    <div className="text-sm text-amber-400 font-mono">{ev.expected_end_time}</div>
                  </div>
                </div>
                
                <div className="flex items-center justify-between mt-4 pt-4 border-t border-slate-800/50">
                  <div className="text-sm text-slate-400">
                    Cause: <span className="text-slate-200">{ev.event_cause}</span>
                  </div>
                  <button 
                    onClick={() => simulateDaemonPoll(ev)}
                    disabled={isPolling}
                    className="flex items-center gap-2 text-xs bg-slate-800 hover:bg-blue-600 text-white px-3 py-1.5 rounded transition-colors disabled:opacity-50"
                  >
                    Force Maps Poll <ChevronRight size={14} />
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>

        <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 h-[500px] flex flex-col">
          <h2 className="text-lg font-semibold flex items-center gap-2 mb-6">
            <Zap size={18} className="text-amber-400" />
            EMA Calibration Feedback Loop
          </h2>

          {!latestInsight ? (
            <div className="flex-1 flex flex-col items-center justify-center text-slate-500 border-2 border-dashed border-slate-800 rounded-xl">
              {isPolling ? (
                <RefreshCw size={32} className="animate-spin text-blue-500 mb-4" />
              ) : (
                <Database size={32} className="mb-4 opacity-50" />
              )}
              <p className="text-sm">Awaiting daemon trigger to process telemetry...</p>
            </div>
          ) : (
            <div className="flex-1 flex flex-col animate-in fade-in slide-in-from-bottom-4 duration-500">
              <div className="bg-blue-500/10 border border-blue-500/20 p-4 rounded-lg mb-6 flex items-start gap-3">
                <CheckCircle2 className="text-blue-400 shrink-0 mt-0.5" size={20} />
                <p className="text-sm text-blue-100 leading-relaxed">{latestInsight.learning_insight}</p>
              </div>

              <div className="grid grid-cols-2 gap-4 mb-6">
                <div className="bg-slate-950 border border-slate-800 p-4 rounded-lg text-center">
                  <div className="text-xs text-slate-500 uppercase tracking-wider mb-2">Original Prediction</div>
                  <div className="text-2xl font-mono text-slate-300">{latestInsight.predicted_severity.toFixed(2)}</div>
                </div>
                <div className="bg-slate-950 border border-slate-800 p-4 rounded-lg text-center">
                  <div className="text-xs text-slate-500 uppercase tracking-wider mb-2">Google Maps Reality</div>
                  <div className="text-2xl font-mono text-rose-400">{latestInsight.observed_severity.toFixed(2)}</div>
                </div>
              </div>

              <div className="mt-auto bg-slate-950 border border-slate-800 p-5 rounded-lg">
                <div className="text-xs text-slate-500 uppercase tracking-wider mb-3">Permanent Multiplier Update</div>
                
                <div className="flex items-center justify-between text-sm font-mono text-slate-400 bg-slate-900 p-3 rounded border border-slate-800/50 mb-4">
                  <span>(0.7 × {latestInsight.previous_calibration.toFixed(2)})</span>
                  <span>+</span>
                  <span>(0.3 × {(latestInsight.observed_severity / Math.max(latestInsight.predicted_severity, 0.1)).toFixed(2)})</span>
                  <span>=</span>
                  <span className="text-emerald-400 font-bold text-lg">{latestInsight.new_calibration_factor.toFixed(2)}x</span>
                </div>

                <div className="flex items-center justify-between text-xs text-slate-500">
                  <span>Historical Weight</span>
                  <span>Correction Delta</span>
                  <span>New State</span>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
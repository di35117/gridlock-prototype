'use client';
import React, { useState } from 'react';
import { Globe, Cpu, Radio, AlertOctagon, ArrowRight, ShieldAlert, CheckCircle2, Terminal } from 'lucide-react';

interface OSINTResult {
  extracted_data: {
    event_id: string;
    corridor: string;
    event_cause: string;
    expected_crowd: number;
    start_time: string;
  };
  forecasted_risk: number;
  registration_message: string;
}

export default function OSINTHarvester() {
  const [inputText, setInputText] = useState("Just heard there's going to be a massive protest march on Mysore Road tomorrow afternoon around 3 PM. Expecting at least 5000 people to show up. Avoid the area completely!");
  const [source, setSource] = useState("Twitter / X");
  const [processStage, setProcessStage] = useState<0 | 1 | 2 | 3>(0);
  const [result, setResult] = useState<OSINTResult | null>(null);

  const simulateWebhook = () => {
    setProcessStage(1);
    setResult(null);
    setTimeout(() => {
      setProcessStage(2);
      setTimeout(() => {
        setResult({
          extracted_data: {
            event_id: "OSINT-9A4F2B",
            corridor: "Mysore Road",
            event_cause: "protest",
            expected_crowd: 5000,
            start_time: new Date(Date.now() + 86400000).toISOString(),
          },
          forecasted_risk: 8.4,
          registration_message: "Event OSINT-9A4F2B queued for autonomous post-event analysis."
        });
        setProcessStage(3);
      }, 1500);
    }, 2000);
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-50 p-6 font-sans">
      <header className="flex justify-between items-center mb-8 border-b border-slate-800 pb-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight flex items-center gap-2">
            <Globe className="text-emerald-500" />
            Social OSINT Harvester
          </h1>
          <p className="text-slate-400 text-sm mt-1">Autonomous Unstructured Intel Processing Pipeline</p>
        </div>
        {processStage === 3 && result?.forecasted_risk && result.forecasted_risk > 7 && (
          <div className="flex items-center gap-2 px-4 py-2 bg-rose-500/10 text-rose-400 rounded border border-rose-500/20 text-sm font-bold animate-pulse">
            <AlertOctagon size={16} />
            <span>WEBSOCKET BROADCAST: ACTIVE</span>
          </div>
        )}
      </header>

      <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 flex flex-col">
          <h2 className="text-lg font-semibold flex items-center gap-2 mb-4">
            <Radio size={18} className="text-slate-400" />
            Raw Signal Intercept
          </h2>
          
          <div className="flex items-center gap-3 mb-4">
            <span className="text-xs font-semibold uppercase tracking-wider text-slate-500">Source Payload:</span>
            <select 
              value={source}
              onChange={(e) => setSource(e.target.value)}
              className="bg-slate-950 border border-slate-800 rounded px-3 py-1 text-sm outline-none focus:border-emerald-500"
            >
              <option>Twitter / X</option>
              <option>Dataminr Webhook</option>
              <option>Police Radio Transcripts</option>
            </select>
          </div>

          <textarea
            value={inputText}
            onChange={(e) => setInputText(e.target.value)}
            className="w-full flex-1 bg-slate-950 border border-slate-800 rounded-lg p-4 text-slate-300 focus:outline-none focus:ring-1 focus:ring-emerald-500 resize-none font-mono text-sm leading-relaxed"
            placeholder="Paste raw unstructured intelligence here..."
          />

          <button 
            onClick={simulateWebhook}
            disabled={processStage !== 0 && processStage !== 3}
            className="w-full mt-4 bg-emerald-600 hover:bg-emerald-700 disabled:bg-slate-800 disabled:text-slate-500 text-white font-medium py-3 rounded-lg transition-colors flex justify-center items-center gap-2"
          >
            {processStage === 0 || processStage === 3 ? (
               <>Inject Payload into Pipeline <ArrowRight size={18} /></>
            ) : "Pipeline Processing..."}
          </button>
        </div>

        <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 relative overflow-hidden flex flex-col">
          {processStage === 3 && result!.forecasted_risk > 7 && (
            <div className="absolute top-0 left-0 w-full h-1 bg-rose-500 animate-pulse"></div>
          )}

          <h2 className="text-lg font-semibold flex items-center gap-2 mb-6">
            <Cpu size={18} className="text-emerald-400" />
            Autonomous Processing Engine
          </h2>

          <div className="flex justify-between items-center mb-8 px-2 relative">
            <div className="absolute top-1/2 left-0 w-full h-0.5 bg-slate-800 -z-10 -translate-y-1/2"></div>
            {[
               { stage: 1, label: "Gemini NER Extraction", icon: Terminal },
               { stage: 2, label: "ML Risk Forecasting", icon: ShieldAlert },
               { stage: 3, label: "System Broadcast", icon: Radio }
            ].map((step, idx) => {
              const isActive = processStage === step.stage;
              const isPast = processStage > step.stage;
              return (
                <div key={idx} className="flex flex-col items-center gap-2 bg-slate-900 px-2">
                  <div className={`w-10 h-10 rounded-full border-2 flex items-center justify-center transition-all ${
                    isActive ? "border-emerald-400 bg-emerald-400/10 text-emerald-400 animate-pulse" :
                    isPast ? "border-emerald-500 bg-emerald-500 text-slate-900" :
                    "border-slate-700 bg-slate-800 text-slate-500"
                  }`}>
                    {isPast ? <CheckCircle2 size={20} /> : <step.icon size={18} />}
                  </div>
                  <span className={`text-xs font-semibold ${isActive || isPast ? "text-slate-200" : "text-slate-500"}`}>
                    {step.label}
                  </span>
                </div>
              );
            })}
          </div>

          <div className="flex-1 bg-slate-950 rounded-lg border border-slate-800 p-4 font-mono text-sm overflow-y-auto">
            {processStage === 0 && <div className="h-full flex items-center justify-center text-slate-600">Awaiting incoming webhook payload...</div>}
            {processStage === 1 && (
              <div className="text-emerald-400 flex flex-col gap-2">
                <p>{`> Initializing Gemini 1.5 Flash Model...`}</p>
                <p className="animate-pulse">{`> Parsing unstructured text for spatial-temporal entities...`}</p>
              </div>
            )}
            {processStage === 2 && (
              <div className="text-blue-400 flex flex-col gap-2">
                <p className="text-emerald-400">{`> JSON Schema Extracted successfully.`}</p>
                <p>{`> Routing to LightGBM Forecaster...`}</p>
                <p className="animate-pulse">{`> Calculating compound risk score for Mysore Road...`}</p>
              </div>
            )}
            {processStage === 3 && result && (
              <div className="space-y-4 animate-in fade-in duration-500">
                <div className="text-emerald-400">{`> Pipeline Execution Complete.`}</div>
                <div className="bg-slate-900 p-3 rounded border border-slate-800">
                  <span className="text-slate-500 block mb-1 uppercase text-xs">Structured Output</span>
                  <div className="grid grid-cols-2 gap-y-2">
                    <div className="text-slate-400">Corridor:</div><div className="text-white">{result.extracted_data.corridor}</div>
                    <div className="text-slate-400">Event Cause:</div><div className="text-white">{result.extracted_data.event_cause}</div>
                    <div className="text-slate-400">Est. Crowd:</div><div className="text-white">{result.extracted_data.expected_crowd}</div>
                  </div>
                </div>
                <div className={`p-3 rounded border ${result.forecasted_risk > 7 ? 'bg-rose-500/10 border-rose-500/30' : 'bg-amber-500/10 border-amber-500/30'}`}>
                   <span className="text-slate-500 block mb-1 uppercase text-xs">Predicted Impact</span>
                   <div className="flex items-end gap-2">
                     <span className={`text-2xl font-bold ${result.forecasted_risk > 7 ? 'text-rose-400' : 'text-amber-400'}`}>{result.forecasted_risk.toFixed(1)}</span>
                     <span className="text-slate-400 mb-1">/ 10 Risk Score</span>
                   </div>
                </div>
                <div className="text-slate-500 text-xs mt-4 border-t border-slate-800 pt-3">
                  {`> Daemon: ${result.registration_message}`}
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
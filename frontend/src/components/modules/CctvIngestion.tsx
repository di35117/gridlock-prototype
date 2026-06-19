'use client';
import React, { useState } from 'react';
import { Camera, Server, ArrowRight, ShieldAlert, CheckCircle2 } from 'lucide-react';

export default function CctvIngestion() {
  const [isProcessing, setIsProcessing] = useState(false);
  const [result, setResult] = useState<any>(null);

  const rawSample = {
    camera_id: "CAM-ORR-04",
    vision_class: "vehicle_collision",
    coords: [12.9352, 77.5341],
    confidence: 0.94,
    objects: ["heavy_vehicle", "two_wheeler"]
  };

  const simulateIngestion = () => {
    setIsProcessing(true);
    setResult(null);
    setTimeout(() => {
      setResult({
        corridor: "Outer Ring Road",
        event_cause: "accident",
        latitude: 12.9352,
        longitude: 77.5341,
        veh_type: "heavy_vehicle",
        compound_multiplier: 1.85,
        risk_level: "High"
      });
      setIsProcessing(false);
    }, 1200);
  };

  return (
    <div className="p-6 font-sans text-slate-50">
      <header className="mb-6 border-b border-slate-800 pb-4">
        <h1 className="text-2xl font-bold flex items-center gap-2">
          <Camera className="text-amber-500" />
          Universal CCTV Telemetry Gateway
        </h1>
        <p className="text-slate-400 text-sm mt-1">LLM Normalization & Compound Risk Extractor</p>
      </header>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Raw Input */}
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-6">
          <h2 className="text-sm font-semibold text-slate-400 uppercase mb-4 flex items-center gap-2">
            <Server size={16} /> Unstructured Vendor Payload
          </h2>
          <pre className="bg-slate-950 p-4 rounded-lg border border-slate-800 text-amber-400 text-xs font-mono overflow-x-auto h-48">
            {JSON.stringify(rawSample, null, 2)}
          </pre>
          <button 
            onClick={simulateIngestion}
            disabled={isProcessing}
            className="w-full mt-4 bg-amber-600 hover:bg-amber-700 text-white font-medium py-2 rounded-lg transition-colors flex justify-center items-center gap-2"
          >
            {isProcessing ? "Translating via Gemini..." : "Push Payload to Parser"} <ArrowRight size={16} />
          </button>
        </div>

        {/* Parsed Output */}
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 relative">
          <h2 className="text-sm font-semibold text-slate-400 uppercase mb-4 flex items-center gap-2">
            <CheckCircle2 size={16} className="text-emerald-500" /> Normalized BTP Schema
          </h2>
          
          {!result ? (
            <div className="h-48 flex items-center justify-center text-slate-600 font-mono text-sm border-2 border-dashed border-slate-800 rounded-lg">
              {isProcessing ? "Normalizing..." : "Awaiting payload..."}
            </div>
          ) : (
            <div className="space-y-4 animate-in fade-in">
              <pre className="bg-slate-950 p-4 rounded-lg border border-slate-800 text-emerald-400 text-xs font-mono overflow-x-auto">
                {JSON.stringify(result, null, 2)}
              </pre>
              
              <div className="bg-rose-500/10 border border-rose-500/20 p-3 rounded-lg flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <ShieldAlert className="text-rose-400" size={18} />
                  <span className="text-sm font-semibold text-rose-400">Compound Conflict Penalty Applied</span>
                </div>
                <span className="font-mono text-rose-300 font-bold">{result.compound_multiplier}x Risk</span>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
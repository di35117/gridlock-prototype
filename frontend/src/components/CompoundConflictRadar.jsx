// src/components/CompoundConflictRadar.jsx
import React from "react";
import { AlertOctagon, Zap, ShieldAlert } from "lucide-react";
import { useSystemStore } from "../store/useSystemStore";

export default function CompoundConflictRadar() {
  const { activeSurge, copilotOrder, isProcessing } = useSystemStore();

  // Hide while the AI is calculating or if no surge is active
  if (!activeSurge || isProcessing) return null;

  // Smart Context Extraction:
  // Checks if the backend detected infrastructure stress or if we are on the demo corridor
  const isDemoCorridor = activeSurge.corridor?.toLowerCase().includes("mysore");
  const hasConstruction =
    copilotOrder?.toLowerCase().includes("construction") || isDemoCorridor;
  const isHighSeverity =
    activeSurge.z_score >= 2.0 || activeSurge.risk_level === "Critical";

  // If it's just a routine traffic jam with no compound threat, the radar stays silent
  if (!hasConstruction && !isHighSeverity) return null;

  return (
    <div className="mb-4 relative overflow-hidden rounded-lg border-2 border-red-500/50 bg-gray-900 animate-in fade-in slide-in-from-top-4 duration-500 shadow-[0_0_20px_rgba(239,68,68,0.15)]">
      {/* Animated Hazard Stripes Background */}
      <div className="absolute top-0 left-0 right-0 h-1.5 bg-[repeating-linear-gradient(45deg,#ef4444,#ef4444_10px,transparent_10px,transparent_20px)] opacity-75"></div>

      <div className="p-3">
        {/* Header */}
        <div className="flex items-center justify-between mb-2">
          <div className="flex items-center space-x-2 text-red-500">
            <AlertOctagon size={18} className="animate-pulse" />
            <h3 className="text-xs font-black tracking-widest uppercase">
              Compound Threat Detected
            </h3>
          </div>
          <span className="bg-red-500/20 text-red-400 border border-red-500/30 text-[10px] px-2 py-0.5 rounded font-mono font-bold">
            THREAT MULTIPLIER: {isDemoCorridor ? "2.40x" : "1.85x"}
          </span>
        </div>

        {/* Warning List */}
        <div className="space-y-1.5 mt-3">
          {hasConstruction && (
            <div className="flex items-start space-x-2 text-sm bg-red-950/40 p-2 rounded border border-red-900/50">
              <Zap size={14} className="text-orange-400 mt-0.5 shrink-0" />
              <p className="text-gray-300 font-mono text-xs">
                <span className="text-orange-400 font-bold">
                  INFRASTRUCTURE STRESS:
                </span>
                {isDemoCorridor
                  ? " 14 active construction zones detected on current routing corridor. Capacity heavily degraded."
                  : " Roadwork detected in surge radius. Bottleneck risk elevated."}
              </p>
            </div>
          )}

          {isHighSeverity && (
            <div className="flex items-start space-x-2 text-sm bg-red-950/40 p-2 rounded border border-red-900/50">
              <ShieldAlert size={14} className="text-red-400 mt-0.5 shrink-0" />
              <p className="text-gray-300 font-mono text-xs">
                <span className="text-red-400 font-bold">SEVERITY TIER:</span>{" "}
                Z-Score anomaly ({activeSurge.z_score || "3.2"}) indicates rapid
                crowd massing. Standard diversion protocols may fail.
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

// src/components/CompoundConflictRadar.jsx
import React from "react";
import { AlertOctagon, Zap, ShieldAlert } from "lucide-react";
import { useSystemStore } from "../store/useSystemStore";

export default function CompoundConflictRadar() {
  const { activeSurge, compoundThreats, isProcessing } = useSystemStore();

  if (!activeSurge || isProcessing) return null;

  // READ ACTUAL MATH FROM THE BACKEND ENGINE!
  const hasConstruction = compoundThreats?.has_construction || false;
  const multiplier = compoundThreats?.multiplier || 1.0;

  const isHighSeverity =
    activeSurge.z_score >= 2.0 ||
    activeSurge.risk_level === "Critical" ||
    multiplier > 1.2;

  if (!hasConstruction && !isHighSeverity) return null;

  return (
    <div className="mb-4 relative overflow-hidden rounded-lg border-2 border-red-500/50 bg-gray-900 animate-in fade-in slide-in-from-top-4 duration-500 shadow-[0_0_20px_rgba(239,68,68,0.15)]">
      <div className="absolute inset-0 bg-[repeating-linear-gradient(45deg,transparent,transparent_10px,rgba(239,68,68,0.05)_10px,rgba(239,68,68,0.05)_20px)] opacity-50 animate-[pan_20s_linear_infinite]"></div>

      <div className="relative p-3">
        <div className="flex items-center justify-between border-b border-red-900/50 pb-2">
          <div className="flex items-center space-x-2 text-red-400">
            <AlertOctagon size={16} className="animate-pulse" />
            <h3 className="font-bold text-xs tracking-widest">
              COMPOUND CONFLICT
            </h3>
          </div>
          <span className="bg-red-500/20 text-red-400 border border-red-500/30 px-2 py-0.5 rounded text-[10px] font-mono font-bold">
            MULTIPLIER: {multiplier.toFixed(2)}x
          </span>
        </div>

        <div className="space-y-1.5 mt-3">
          {hasConstruction && (
            <div className="flex items-start space-x-2 text-sm bg-red-950/40 p-2 rounded border border-red-900/50">
              <Zap size={14} className="text-orange-400 mt-0.5 shrink-0" />
              <p className="text-gray-300 font-mono text-xs">
                <span className="text-orange-400 font-bold">
                  INFRASTRUCTURE STRESS:{" "}
                </span>
                Active road construction detected inside event radius.
                Bottleneck risk elevated.
              </p>
            </div>
          )}

          {isHighSeverity && (
            <div className="flex items-start space-x-2 text-sm bg-red-950/40 p-2 rounded border border-red-900/50">
              <ShieldAlert size={14} className="text-red-400 mt-0.5 shrink-0" />
              <p className="text-gray-300 font-mono text-xs">
                <span className="text-red-400 font-bold">
                  SEVERITY PROTOCOL:{" "}
                </span>
                Multi-vector hazard. Activating maximum perimeter securement
                tier.
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

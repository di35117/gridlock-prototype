import React from "react";
import { Shield, Ambulance, Flame, HardHat } from "lucide-react";
import { useSystemStore } from "../store/useSystemStore";

export default function TacticalResourceDashboard() {
  const { resources, activeSurge, isProcessing } = useSystemStore();

  if (!activeSurge) return null;

  // Local fallback calculations ensure structural preservation if worker values are empty
  const fallbackMath = {
    police: Math.ceil((activeSurge.expected_crowd || 1000) / 200),
    traffic: Math.ceil((activeSurge.expected_crowd || 1000) / 400),
    ambulance: activeSurge.risk_level === "Critical" ? 3 : 1,
    fire:
      activeSurge.event_cause === "fire" ||
      activeSurge.risk_level === "Critical"
        ? 2
        : 0,
    status: "Optimal Deployment Vector",
  };

  const displayData = resources || fallbackMath;

  return (
    <div className="mb-4 bg-gray-900 border border-gray-700 rounded-lg overflow-hidden shadow-md animate-fade-in">
      <div className="bg-gray-950 px-4 py-2 border-b border-gray-700 flex justify-between items-center">
        <h4 className="text-[11px] font-black tracking-widest font-mono text-gray-400 flex items-center gap-1.5">
          <HardHat size={14} className="text-blue-400" />
          OPTIMIZED FIELD RESOURCE COMMITTAL
        </h4>
        <span className="text-[9px] font-mono font-bold px-2 py-0.5 bg-green-500/10 text-green-400 border border-green-500/20 rounded">
          {isProcessing ? "RE-OPTIMIZING..." : "STATE: LOCKED"}
        </span>
      </div>

      <div className="grid grid-cols-4 gap-px bg-gray-800">
        {/* Law Enforcement Force */}
        <div className="bg-gray-900 p-3 flex flex-col items-center justify-center relative overflow-hidden group">
          <div className="absolute inset-0 bg-blue-500/5 translate-y-full group-hover:translate-y-0 transition-transform"></div>
          <Shield size={20} className="text-blue-400 mb-1" />
          <span className="text-2xl font-black text-gray-100">
            {displayData.police || displayData.law_enforcement || 0}
          </span>
          <span className="text-[9px] text-gray-500 font-mono tracking-wider">
            LAW FORCE
          </span>
        </div>

        {/* Traffic Enforcement */}
        <div className="bg-gray-900 p-3 flex flex-col items-center justify-center relative overflow-hidden group">
          <div className="absolute inset-0 bg-yellow-500/5 translate-y-full group-hover:translate-y-0 transition-transform"></div>
          <Shield size={20} className="text-yellow-400 mb-1" />
          <span className="text-2xl font-black text-gray-100">
            {displayData.traffic || displayData.traffic_units || 0}
          </span>
          <span className="text-[9px] text-gray-500 font-mono tracking-wider">
            TRAFFIC
          </span>
        </div>

        {/* EMS/Medical */}
        <div className="bg-gray-900 p-3 flex flex-col items-center justify-center relative overflow-hidden group">
          <div className="absolute inset-0 bg-red-500/5 translate-y-full group-hover:translate-y-0 transition-transform"></div>
          <Ambulance size={20} className="text-red-400 mb-1" />
          <span className="text-2xl font-black text-gray-100">
            {displayData.ambulance || displayData.medical_units || 0}
          </span>
          <span className="text-[9px] text-gray-500 font-mono tracking-wider">
            EMS/MED
          </span>
        </div>

        {/* Fire Operations */}
        <div className="bg-gray-900 p-3 flex flex-col items-center justify-center relative overflow-hidden group">
          <div className="absolute inset-0 bg-orange-500/5 translate-y-full group-hover:translate-y-0 transition-transform"></div>
          <Flame size={20} className="text-orange-400 mb-1" />
          <span className="text-2xl font-black text-gray-100">
            {displayData.fire || displayData.fire_tenders || 0}
          </span>
          <span className="text-[9px] text-gray-500 font-mono tracking-wider">
            FIRE RESCUE
          </span>
        </div>
      </div>
    </div>
  );
}

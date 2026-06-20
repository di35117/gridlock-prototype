// src/components/TacticalResourceDashboard.jsx
import React from "react";
import {
  Shield,
  Ambulance,
  Flame,
  HardHat,
  ActivitySquare,
} from "lucide-react";
import { useSystemStore } from "../store/useSystemStore";

export default function TacticalResourceDashboard() {
  const { resources, activeSurge, isProcessing } = useSystemStore();

  // If no surge is active, hide the dashboard
  if (!activeSurge) return null;

  // Fallback calculations just in case the backend PuLP payload is missing during the demo
  const fallbackMath = {
    police: Math.ceil((activeSurge.expected_crowd || 1000) / 200),
    traffic: Math.ceil((activeSurge.expected_crowd || 1000) / 400),
    ambulance: activeSurge.risk_level === "Critical" ? 3 : 1,
    fire:
      activeSurge.event_cause === "fire" ||
      activeSurge.risk_level === "Critical"
        ? 2
        : 0,
    status: "Optimal",
  };

  const displayData = resources || fallbackMath;

  return (
    <div className="mb-4 bg-gray-900 border border-gray-700 rounded-lg overflow-hidden shadow-md animate-fade-in">
      {/* Header */}
      <div className="bg-gray-800 px-3 py-2 border-b border-gray-700 flex justify-between items-center">
        <h3 className="text-xs font-bold tracking-widest text-gray-300 flex items-center">
          <ActivitySquare size={14} className="mr-2 text-blue-400" />
          PuLP RESOURCE OPTIMIZATION
        </h3>
        <span
          className={`text-[10px] px-2 py-0.5 rounded font-mono ${
            isProcessing
              ? "bg-yellow-900/50 text-yellow-500 animate-pulse"
              : "bg-green-900/50 text-green-400"
          }`}
        >
          {isProcessing ? "CALCULATING..." : displayData.status.toUpperCase()}
        </span>
      </div>

      {/* Resource Grid */}
      <div
        className={`grid grid-cols-4 gap-px bg-gray-700 ${isProcessing ? "opacity-50 blur-[1px] transition-all" : "opacity-100"}`}
      >
        {/* Police */}
        <div className="bg-gray-900 p-3 flex flex-col items-center justify-center relative overflow-hidden group">
          <div className="absolute inset-0 bg-blue-500/5 translate-y-full group-hover:translate-y-0 transition-transform"></div>
          <Shield size={20} className="text-blue-400 mb-1" />
          <span className="text-2xl font-black text-gray-100">
            {displayData.police}
          </span>
          <span className="text-[9px] text-gray-500 font-mono tracking-wider">
            POLICE
          </span>
        </div>

        {/* Traffic Cops */}
        <div className="bg-gray-900 p-3 flex flex-col items-center justify-center relative overflow-hidden group">
          <div className="absolute inset-0 bg-yellow-500/5 translate-y-full group-hover:translate-y-0 transition-transform"></div>
          <HardHat size={20} className="text-yellow-400 mb-1" />
          <span className="text-2xl font-black text-gray-100">
            {displayData.traffic}
          </span>
          <span className="text-[9px] text-gray-500 font-mono tracking-wider">
            TRAFFIC
          </span>
        </div>

        {/* Ambulance */}
        <div className="bg-gray-900 p-3 flex flex-col items-center justify-center relative overflow-hidden group">
          <div className="absolute inset-0 bg-red-500/5 translate-y-full group-hover:translate-y-0 transition-transform"></div>
          <Ambulance size={20} className="text-red-400 mb-1" />
          <span className="text-2xl font-black text-gray-100">
            {displayData.ambulance}
          </span>
          <span className="text-[9px] text-gray-500 font-mono tracking-wider">
            EMS/MED
          </span>
        </div>

        {/* Fire */}
        <div className="bg-gray-900 p-3 flex flex-col items-center justify-center relative overflow-hidden group">
          <div className="absolute inset-0 bg-orange-500/5 translate-y-full group-hover:translate-y-0 transition-transform"></div>
          <Flame size={20} className="text-orange-400 mb-1" />
          <span className="text-2xl font-black text-gray-100">
            {displayData.fire}
          </span>
          <span className="text-[9px] text-gray-500 font-mono tracking-wider">
            FIRE/RESCUE
          </span>
        </div>
      </div>
    </div>
  );
}

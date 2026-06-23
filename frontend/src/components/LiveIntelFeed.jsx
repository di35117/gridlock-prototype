import React from "react";
import { useSystemStore } from "../store/useSystemStore";
import { AlertTriangle, Radio, Video, Activity } from "lucide-react";

export default function LiveIntelFeed() {
  const { intelFeed, triggerSurgeResponse } = useSystemStore();

  const getIcon = (type, source) => {
    if (type === "CCTV_ANOMALY")
      return <Video size={16} className="text-purple-400" />;
    if (type === "CRITICAL_ALERT" && source?.includes("OSINT"))
      return <Radio size={16} className="text-blue-400" />;
    if (type === "TRAFFIC_SURGE" || type === "SURGE_ALERT")
      return <Activity size={16} className="text-red-400" />;
    return <AlertTriangle size={16} className="text-yellow-400" />;
  };

  const getBorderColor = (risk) => {
    if (risk === "Critical") return "border-red-500/50 bg-red-900/20";
    if (risk === "High") return "border-orange-500/50 bg-orange-900/20";
    return "border-gray-700 bg-gray-800/50";
  };

  return (
    <div className="w-80 bg-gray-900 border-l border-gray-700 flex flex-col h-full overflow-hidden">
      <div className="p-4 border-b border-gray-700 flex items-center justify-between bg-gray-950">
        <h3 className="text-xs font-black tracking-widest font-mono text-gray-400 flex items-center gap-1.5">
          <span className="w-2 h-2 rounded-full bg-red-500 animate-ping"></span>
          REALTIME STREAM FEED
        </h3>
        <span className="text-[10px] font-mono font-bold text-gray-500 bg-gray-800 px-2 py-0.5 rounded">
          {intelFeed.length} EVENTS ACTIVE
        </span>
      </div>

      <div className="flex-1 overflow-y-auto p-4 space-y-3 custom-scrollbar">
        {intelFeed.length === 0 ? (
          <div className="h-full flex flex-col items-center justify-center text-center p-4">
            <Radio size={24} className="text-gray-600 animate-pulse mb-2" />
            <p className="text-xs font-mono text-gray-500">
              AWAITING SENSOR SIGNALS ON RADAR TUNNEL...
            </p>
          </div>
        ) : (
          intelFeed.map((alert, index) => (
            <div
              key={alert.id || index}
              onClick={() => triggerSurgeResponse(alert.payload || alert)}
              className={`p-3 rounded border text-sm cursor-pointer hover:bg-gray-800 transition-colors animate-fade-in ${getBorderColor(alert.risk_level)}`}
            >
              <div className="flex items-center justify-between mb-1">
                <div className="flex items-center space-x-2">
                  {getIcon(alert.type, alert.source)}
                  <span className="text-xs font-bold text-gray-200">
                    {alert.source || "ASTRAM Sensor"}
                  </span>
                </div>
                <span className="text-[10px] text-gray-500">
                  {new Date(alert.timestamp || Date.now()).toLocaleTimeString(
                    [],
                    { hour: "2-digit", minute: "2-digit" },
                  )}
                </span>
              </div>
              <p className="text-gray-300 text-xs mt-1">
                {alert.message ||
                  `Surge detected on ${alert.corridor || alert.payload?.corridor}`}
              </p>
              {alert.corridor && (
                <div className="mt-2 text-[10px] font-mono text-gray-400 bg-gray-950 px-2 py-1 rounded inline-block">
                  LOC: {alert.corridor.toUpperCase()}
                </div>
              )}
            </div>
          ))
        )}
      </div>
    </div>
  );
}

// src/App.jsx
import React, { useEffect } from "react";
import ReactMarkdown from "react-markdown";
import { Activity, Cpu } from "lucide-react";
import BengaluruMap from "./components/BengaluruMap";
import LiveIntelFeed from "./components/LiveIntelFeed";
import TacticalResourceDashboard from "./components/TacticalResourceDashboard";
import CompoundConflictRadar from "./components/CompoundConflictRadar";
import { connectSystemWebSocket } from "./services/websocket";
import { useSystemStore } from "./store/useSystemStore";

function App() {
  const { activeSurge, copilotOrder, isProcessing } = useSystemStore();

  useEffect(() => {
    connectSystemWebSocket();
  }, []);

  return (
    <div className="flex flex-col h-screen bg-gray-900 text-gray-100 overflow-hidden font-sans">
      {/* Header */}
      <header className="flex items-center justify-between px-6 py-3 bg-gray-800 border-b border-gray-700 shadow-md z-10">
        <div className="flex items-center space-x-3">
          <Activity className="text-blue-400" size={24} />
          <h1 className="text-xl font-bold tracking-wider">
            BTP EVENT COMMAND
          </h1>
        </div>
        <div className="text-sm font-mono text-green-400 flex items-center">
          <span className="w-2 h-2 rounded-full bg-green-500 mr-2 animate-pulse"></span>
          AUTONOMOUS SYSTEMS ACTIVE
        </div>
      </header>

      <main className="flex flex-1 overflow-hidden">
        {/* Left: Live ML Road Map */}
        <section className="flex-1 relative border-r border-gray-800">
          <BengaluruMap />
        </section>

        {/* Middle: AI Copilot & Tactical Sidebar */}
        <aside className="w-[420px] bg-gray-800 flex flex-col overflow-hidden shadow-xl z-10">
          <div className="p-4 border-b border-gray-700 bg-gray-900 flex items-center text-blue-400 shrink-0">
            <Cpu className="mr-2" size={20} />
            <h2 className="font-semibold tracking-wide">AI TACTICAL COPILOT</h2>
          </div>

          <div className="flex-1 overflow-y-auto p-4 custom-scrollbar">
            {!activeSurge ? (
              <div className="text-center text-gray-500 font-mono mt-10 animate-pulse">
                Monitoring corridor network...
                <br />
                Awaiting surge telemetry.
              </div>
            ) : isProcessing ? (
              <div className="space-y-4">
                <div className="p-3 bg-red-900/30 border border-red-500 rounded text-sm font-mono text-red-400 shadow-[0_0_10px_rgba(239,68,68,0.2)]">
                  CRITICAL SURGE DETECTED: {activeSurge.corridor}
                </div>
                <div className="text-center text-gray-400 font-mono text-sm animate-pulse pt-4">
                  Executing LightGBM Forecaster...
                  <br />
                  Calculating Routing Diversions...
                  <br />
                  Drafting Gemini Operational Order...
                </div>
              </div>
            ) : (
              <div className="space-y-4 animate-fade-in">
                {/* 1. Context Awareness Widget */}
                <CompoundConflictRadar />

                {/* 2. Operations Research Math Widget */}
                <TacticalResourceDashboard />

                {/* 3. The LLM Output */}
                <div className="prose prose-invert prose-sm max-w-none bg-gray-900/50 p-4 rounded-lg border border-gray-700">
                  {copilotOrder ? (
                    <ReactMarkdown>{copilotOrder}</ReactMarkdown>
                  ) : (
                    <div className="text-red-400 font-mono">
                      [ERROR] Failed to generate tactical order.
                    </div>
                  )}
                </div>
              </div>
            )}
          </div>
        </aside>

        {/* Right: The Live Intel Feed */}
        <LiveIntelFeed />
      </main>
    </div>
  );
}

export default App;

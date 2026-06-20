// src/App.jsx
import React, { useEffect } from "react";
import ReactMarkdown from "react-markdown";
import { Activity, ShieldAlert, Cpu } from "lucide-react";
import BengaluruMap from "./components/BengaluruMap";
import { connectSystemWebSocket } from "./services/websocket";
import { useSystemStore } from "./store/useSystemStore";

function App() {
  const { activeSurge, copilotOrder, isProcessing } = useSystemStore();

  useEffect(() => {
    connectSystemWebSocket(); // Start listening for surges on load
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

        {/* Right: AI Copilot & Module Intel Sidebar */}
        <aside className="w-[450px] bg-gray-800 flex flex-col overflow-hidden shadow-xl z-10">
          <div className="p-4 border-b border-gray-700 bg-gray-900 flex items-center text-blue-400">
            <Cpu className="mr-2" size={20} />
            <h2 className="font-semibold tracking-wide">AI TACTICAL COPILOT</h2>
          </div>

          <div className="flex-1 overflow-y-auto p-4">
            {!activeSurge ? (
              <div className="text-center text-gray-500 font-mono mt-10 animate-pulse">
                Monitoring corridor network...
                <br />
                Awaiting surge telemetry.
              </div>
            ) : isProcessing ? (
              <div className="space-y-4">
                <div className="p-3 bg-red-900/30 border border-red-500 rounded text-sm font-mono text-red-400">
                  CRITICAL SURGE DETECTED: {activeSurge.corridor}
                </div>
                <div className="text-center text-gray-400 font-mono text-sm animate-pulse">
                  Executing LightGBM Forecaster...
                  <br />
                  Calculating Routing Diversions...
                  <br />
                  Drafting Gemini Operational Order...
                </div>
              </div>
            ) : (
              <div className="space-y-4 animate-fade-in">
                {/* Module Summary Panel */}
                <div className="grid grid-cols-2 gap-2 mb-4">
                  <div className="bg-gray-700 p-2 rounded border border-gray-600">
                    <div className="text-[10px] text-gray-400 font-mono">
                      COMPOUND RISK
                    </div>
                    <div className="text-lg font-bold text-orange-400">
                      High
                    </div>
                  </div>
                  <div className="bg-gray-700 p-2 rounded border border-gray-600">
                    <div className="text-[10px] text-gray-400 font-mono">
                      BARRICADES REQ
                    </div>
                    <div className="text-lg font-bold text-yellow-400">
                      4 Points
                    </div>
                  </div>
                </div>

                {/* Gemini Markdown Output */}
                <div className="prose prose-invert prose-sm max-w-none">
                  {copilotOrder ? (
                    <ReactMarkdown>{copilotOrder}</ReactMarkdown>
                  ) : (
                    <div className="text-red-400">
                      Failed to generate tactical order.
                    </div>
                  )}
                </div>
              </div>
            )}
          </div>
        </aside>
      </main>
    </div>
  );
}

export default App;

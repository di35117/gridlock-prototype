import React, { useEffect } from "react";
import ReactMarkdown from "react-markdown";
import { Activity, Cpu, Loader2 } from "lucide-react";
import { Analytics } from "@vercel/analytics/react";

import BengaluruMap from "./components/BengalurMap.jsx";
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
      <Analytics />

      {/* Primary Header Command Block */}
      <header className="flex items-center justify-between px-6 py-3 bg-gray-800 border-b border-gray-700 shadow-md z-10">
        <div className="flex items-center space-x-3">
          <Activity className="text-blue-400" size={24} />
          <h1 className="text-xl font-bold tracking-wider">
            BTP EVENT COMMAND
          </h1>
        </div>
        <div className="text-sm font-mono text-green-400 flex items-center space-x-2 bg-gray-950 px-3 py-1 rounded border border-gray-800">
          <Cpu size={14} className="animate-spin text-green-500" />
          <span className="tracking-widest">CELERY ENGINE ENGINE ONLINE</span>
        </div>
      </header>

      {/* Main Container Layout */}
      <main className="flex flex-1 overflow-hidden">
        {/* Left Aspect Grid Map Display */}
        <div className="flex-1 h-full relative">
          <BengaluruMap />
        </div>

        {/* Center Lateral Command Matrix */}
        <aside className="w-96 border-l border-r border-gray-700 bg-gray-950 p-4 flex flex-col h-full overflow-y-auto custom-scrollbar shadow-2xl">
          <CompoundConflictRadar />
          <TacticalResourceDashboard />

          <div className="flex-1 flex flex-col min-h-0">
            {isProcessing ? (
              <div className="flex-1 flex flex-col items-center justify-center p-6 border border-dashed border-gray-800 rounded bg-gray-900/40">
                <Loader2 className="w-8 h-8 text-blue-500 animate-spin mb-3" />
                <p className="text-xs font-mono text-blue-400 text-center tracking-wide uppercase">
                  Compiling cross-module operations directives...
                </p>
              </div>
            ) : !activeSurge ? (
              <div className="flex-1 flex flex-col items-center justify-center text-center p-6 border border-dashed border-gray-800 rounded bg-gray-900/20">
                <Activity
                  size={32}
                  className="text-gray-700 mb-2 animate-pulse"
                />
                <p className="text-xs font-mono text-gray-500">
                  AWAITING WEBHOOK TRIGGER SIGNAL FOR AUTOMATED COPILOT INCIDENT
                  DISPATCH
                </p>
              </div>
            ) : (
              <div className="flex-1 flex flex-col bg-gray-900 border border-gray-700 rounded overflow-hidden">
                <div className="bg-gray-950 px-4 py-2 border-b border-gray-700 font-mono text-[10px] font-black tracking-widest text-gray-400">
                  AI OPERATIONAL PLAN DIRECTIVE
                </div>
                <div className="flex-1 overflow-y-auto p-4 custom-markdown-styles">
                  {copilotOrder ? (
                    <ReactMarkdown
                      components={{
                        h1: ({ node, ...props }) => (
                          <h1
                            className="text-base font-black text-blue-400 font-mono mt-4 mb-2 border-b border-gray-800 pb-1"
                            {...props}
                          />
                        ),
                        h2: ({ node, ...props }) => (
                          <h2
                            className="text-sm font-bold text-gray-200 font-mono mt-3 mb-1"
                            {...props}
                          />
                        ),
                        p: ({ node, ...props }) => (
                          <p
                            className="mb-3 text-sm text-gray-300 leading-relaxed font-mono"
                            {...props}
                          />
                        ),
                        ul: ({ node, ...props }) => (
                          <ul
                            className="list-disc list-outside ml-4 mb-3 text-sm text-gray-300 font-mono space-y-1"
                            {...props}
                          />
                        ),
                        strong: ({ node, ...props }) => (
                          <strong
                            className="text-white font-bold bg-gray-800 px-1 rounded"
                            {...props}
                          />
                        ),
                      }}
                    >
                      {copilotOrder}
                    </ReactMarkdown>
                  ) : (
                    <div className="text-red-400 font-mono text-xs">
                      [ERROR] Task orchestration loop timed out or failed to
                      finalize. Check distributed server telemetry log
                      structures.
                    </div>
                  )}
                </div>
              </div>
            )}
          </div>
        </aside>

        {/* Right Panel Layout Contextual Feed */}
        <LiveIntelFeed />
      </main>
    </div>
  );
}

export default App;

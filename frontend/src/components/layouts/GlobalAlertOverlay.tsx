'use client';
import React, { useState, useEffect, useRef } from 'react';
import { Wifi, WifiOff, AlertOctagon, Video, Waves, X, BellRing } from 'lucide-react';

// --- Types matching your backend WebSocket payloads ---
interface BTPAlert {
  id: string;
  type: 'CCTV_ANOMALY' | 'CRITICAL_ALERT' | 'SURGE_ALERT';
  timestamp: string;
  source: string;
  corridor: string;
  risk_level: string;
  message: string;
  ui_action: string;
}

export default function GlobalAlertOverlay() {
  const [alerts, setAlerts] = useState<BTPAlert[]>([]);
  const [wsStatus, setWsStatus] = useState<'connecting' | 'connected' | 'disconnected'>('connecting');
  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    let pingInterval: NodeJS.Timeout;

    const connectWs = () => {
      // Connect to your FastAPI WebSocket router
      const ws = new WebSocket('ws://localhost:8000/api/ws/dashboard');
      wsRef.current = ws;

      ws.onopen = () => {
        setWsStatus('connected');
        // Ping-pong keepalive every 30 seconds
        pingInterval = setInterval(() => {
          if (ws.readyState === WebSocket.OPEN) {
            ws.send('ping');
          }
        }, 30000);
      };

      ws.onmessage = (event) => {
        // Ignore pong responses
        if (event.data === 'pong') return;

        try {
          const payload = JSON.parse(event.data);
          const newAlert: BTPAlert = {
            ...payload,
            id: Math.random().toString(36).substring(7),
          };

          // Prepend new alerts to the top of the feed
          setAlerts((prev) => [newAlert, ...prev]);

          if (payload.ui_action === 'TRIGGER_SIREN_AND_SNAP_MAP') {
             console.log(`[MAP_CMD] Snapping camera to: ${payload.corridor}`);
          }
        } catch (err) {
          console.error("Failed to parse WebSocket message", err);
        }
      };

      ws.onclose = () => {
        setWsStatus('disconnected');
        clearInterval(pingInterval);
        // Auto-reconnect after 5 seconds
        setTimeout(connectWs, 5000);
      };
    };

    connectWs();

    return () => {
      clearInterval(pingInterval);
      wsRef.current?.close();
    };
  }, []);

  const dismissAlert = (id: string) => {
    setAlerts((prev) => prev.filter((a) => a.id !== id));
  };

  return (
    <div className="fixed top-0 right-0 w-96 h-screen p-4 pointer-events-none z-50 flex flex-col">
      
      {/* WebSocket Status Indicator */}
      <div className="flex justify-end mb-4 pointer-events-auto">
        <div className={`flex items-center gap-2 px-3 py-1.5 rounded-full shadow-lg border backdrop-blur-md text-xs font-mono font-semibold ${
          wsStatus === 'connected' ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-400' :
          wsStatus === 'connecting' ? 'bg-amber-500/10 border-amber-500/30 text-amber-400' :
          'bg-rose-500/10 border-rose-500/30 text-rose-400'
        }`}>
          {wsStatus === 'connected' ? <Wifi size={14} /> : <WifiOff size={14} className="animate-pulse" />}
          {wsStatus === 'connected' ? 'WS: CONNECTED' : 'WS: RECONNECTING...'}
        </div>
      </div>

      {/* Alert Feed */}
      <div className="flex-1 overflow-y-auto space-y-3 pointer-events-auto scrollbar-hide">
        {alerts.map((alert) => {
          const styles = {
            'CCTV_ANOMALY': { bg: 'bg-amber-950/90 border-amber-500/50', text: 'text-amber-400', icon: Video },
            'CRITICAL_ALERT': { bg: 'bg-rose-950/90 border-rose-500/50', text: 'text-rose-400', icon: AlertOctagon },
            'SURGE_ALERT': { bg: 'bg-cyan-950/90 border-cyan-500/50', text: 'text-cyan-400', icon: Waves }
          }[alert.type] || { bg: 'bg-slate-900 border-slate-700', text: 'text-slate-300', icon: BellRing };

          const Icon = styles.icon;

          return (
            <div key={alert.id} className={`${styles.bg} border rounded-lg p-4 shadow-2xl backdrop-blur-xl animate-in slide-in-from-right-8 fade-in duration-300 relative group`}>
              <button 
                onClick={() => dismissAlert(alert.id)}
                className="absolute top-2 right-2 text-slate-500 hover:text-white opacity-0 group-hover:opacity-100 transition-opacity"
              >
                <X size={16} />
              </button>

              <div className="flex items-center gap-2 mb-2">
                <Icon size={16} className={`${styles.text} ${alert.type === 'CRITICAL_ALERT' ? 'animate-pulse' : ''}`} />
                <span className={`text-xs font-bold tracking-wider ${styles.text}`}>{alert.type.replace('_', ' ')}</span>
                <span className="text-[10px] font-mono text-slate-400 ml-auto mr-4">
                  {new Date(alert.timestamp).toLocaleTimeString()}
                </span>
              </div>

              <div className="text-white font-semibold text-sm mb-1">{alert.corridor}</div>
              <p className="text-slate-300 text-xs leading-relaxed mb-3">{alert.message}</p>
              
              <div className="flex justify-between items-center mt-2 pt-2 border-t border-slate-800/50">
                <span className="text-[10px] uppercase text-slate-500 font-semibold">{alert.source}</span>
                <button className={`text-xs px-2 py-1 rounded bg-black/30 hover:bg-black/50 transition-colors ${styles.text}`}>
                  Acknowledge
                </button>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
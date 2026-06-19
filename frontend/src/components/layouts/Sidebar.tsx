'use client';
import React from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { LayoutDashboard, BrainCircuit, ShieldAlert, Crosshair, Map } from 'lucide-react';

export default function Sidebar() {
  const pathname = usePathname();

  const navItems = [
    { name: 'Command Center', path: '/dashboard', icon: LayoutDashboard },
    { name: 'Intelligence Hub', path: '/intelligence', icon: ShieldAlert },
    { name: 'ML Forecasting', path: '/forecasting', icon: BrainCircuit },
    { name: 'Tactical Ops', path: '/operations', icon: Crosshair },
  ];

  return (
    <div className="w-64 bg-slate-950 border-r border-slate-800 h-screen flex flex-col">
      <div className="p-6 border-b border-slate-800 flex items-center gap-3">
        <div className="w-8 h-8 bg-blue-600 rounded flex items-center justify-center">
          <Map size={20} className="text-white" />
        </div>
        <div>
          <h1 className="text-lg font-bold text-slate-50 tracking-tight">Gridlock C3</h1>
          <p className="text-[10px] uppercase text-blue-400 font-mono tracking-widest">BTP Ops Terminal</p>
        </div>
      </div>

      <nav className="flex-1 p-4 space-y-2">
        {navItems.map((item) => {
          const isActive = pathname === item.path;
          return (
            <Link key={item.name} href={item.path}>
              <div className={`flex items-center gap-3 px-4 py-3 rounded-lg transition-colors ${
                isActive ? 'bg-blue-600/10 text-blue-400 border border-blue-600/20' : 'text-slate-400 hover:bg-slate-900 hover:text-slate-200'
              }`}>
                <item.icon size={18} />
                <span className="font-medium text-sm">{item.name}</span>
              </div>
            </Link>
          );
        })}
      </nav>

      <div className="p-4 border-t border-slate-800 text-xs font-mono text-slate-600 text-center">
        SYSTEM STATUS: ONLINE
      </div>
    </div>
  );
}
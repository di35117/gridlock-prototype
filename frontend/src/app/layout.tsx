import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import Sidebar from "@/components/layouts/Sidebar";
import GlobalAlertOverlay from "@/components/layouts/GlobalAlertOverlay";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "Gridlock C3 | BTP Ops",
  description: "Bengaluru Traffic Police Command Center",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="dark">
      <body className={`${inter.className} bg-slate-950 flex h-screen overflow-hidden text-slate-50`}>
        {/* WebSocket Siren - Active on all pages */}
        <GlobalAlertOverlay />
        
        {/* Persistent Navigation */}
        <Sidebar />
        
        {/* Scrollable Page Content */}
        <main className="flex-1 overflow-y-auto relative">
          {children}
        </main>
      </body>
    </html>
  );
}
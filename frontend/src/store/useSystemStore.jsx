// src/store/useSystemStore.js
import { create } from "zustand";

export const useSystemStore = create((set) => ({
  // Map Data
  roadMetrics: null, // GeoJSON holding ML predictions for every road

  // Incident Data
  activeSurge: null,

  // AI Copilot & Routing Data
  copilotOrder: null,
  barricades: [], // Array of [lng, lat]
  diversions: null, // GeoJSON LineStrings for routing

  // System Status
  isProcessing: false,

  setRoadMetrics: (data) => set({ roadMetrics: data }),

  // The trigger that resets the board when a new surge hits
  triggerSurgeResponse: (surgeData) =>
    set({
      activeSurge: surgeData,
      isProcessing: true,
      copilotOrder: null,
      barricades: [],
      diversions: null,
    }),

  // Fills the UI once the backend modules finish calculating
  resolveSurgeResponse: (copilotText, barricadeData, diversionData) =>
    set({
      copilotOrder: copilotText,
      barricades: barricadeData,
      diversions: diversionData,
      isProcessing: false,
    }),
}));

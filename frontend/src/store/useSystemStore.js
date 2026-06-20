// src/store/useSystemStore.js
import { create } from "zustand";

export const useSystemStore = create((set) => ({
  roadMetrics: null,
  intelFeed: [],

  activeSurge: null,
  copilotOrder: null,
  barricades: [],
  diversions: null,
  resources: null, // <-- ADD THIS
  isProcessing: false,

  setRoadMetrics: (data) => set({ roadMetrics: data }),

  addIntelAlert: (alert) =>
    set((state) => ({
      intelFeed: [alert, ...state.intelFeed].slice(0, 50),
    })),

  triggerSurgeResponse: (surgeData) =>
    set({
      activeSurge: surgeData,
      isProcessing: true,
      copilotOrder: null,
      barricades: [],
      diversions: null,
      resources: null, // <-- RESET THIS
    }),

  // <-- UPDATE THIS FUNCTION TO ACCEPT resourceData
  resolveSurgeResponse: (
    copilotText,
    barricadeData,
    diversionData,
    resourceData,
  ) =>
    set({
      copilotOrder: copilotText,
      barricades: barricadeData,
      diversions: diversionData,
      resources: resourceData,
      isProcessing: false,
    }),
}));

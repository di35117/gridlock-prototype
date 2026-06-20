// src/store/useSystemStore.js
import { create } from "zustand";

export const useSystemStore = create((set) => ({
  // Map Data
  roadMetrics: null,

  // Event Inbox (Solves the multiple-surge problem)
  intelFeed: [], // Stores every incoming WS alert

  // Currently Focused Incident Data
  activeSurge: null,
  copilotOrder: null,
  barricades: [],
  diversions: null,
  isProcessing: false,

  setRoadMetrics: (data) => set({ roadMetrics: data }),

  // Adds an alert to the top of the feed (keeps the last 50)
  addIntelAlert: (alert) =>
    set((state) => ({
      intelFeed: [alert, ...state.intelFeed].slice(0, 50),
    })),

  // The trigger that resets the board when a new surge hits (or when clicked from the feed)
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

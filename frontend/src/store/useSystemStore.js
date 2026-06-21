import { create } from "zustand";
import { persist } from "zustand/middleware"; // <-- Add this import

export const useSystemStore = create(
  persist(
    (set) => ({
      roadMetrics: null,
      intelFeed: [],
      activeSurge: null,
      copilotOrder: null,
      barricades: [],
      diversions: null,
      resources: null,
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
          resources: null,
        }),

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
    }),
    {
      name: "btp-command-storage", // <-- This saves it to Local Storage!
    },
  ),
);

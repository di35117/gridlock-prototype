import { create } from "zustand";
import { persist } from "zustand/middleware";

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
      compoundThreats: null,
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
          compoundThreats: null,
        }),

      resolveSurgeResponse: (
        copilotText,
        barricadeData,
        diversionData,
        resourceData,
        threatData,
      ) =>
        set({
          copilotOrder: copilotText,
          barricades: barricadeData,
          diversions: diversionData,
          resources: resourceData,
          compoundThreats: threatData,
          isProcessing: false,
        }),
    }),
    { name: "gridlock-system-store" },
  ),
);

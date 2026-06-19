import ImpactForecaster from "@/components/modules/ImpactForecaster";
import LearningEngineDashboard from "@/components/modules/LearningEngine";
import SurgeDetectorEngine from "@/components/modules/SurgeMonitor";

export default function ForecastingPage() {
  return (
    <div className="flex flex-col gap-8 pb-12">
      <SurgeDetectorEngine />
      <div className="px-6 border-t border-slate-800 pt-8 mt-4">
        <ImpactForecaster />
      </div>
      <div className="px-6 border-t border-slate-800 pt-8 mt-4">
        <LearningEngineDashboard />
      </div>
    </div>
  );
}
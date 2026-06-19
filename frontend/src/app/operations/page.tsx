import ResourceRecommender from "@/components/modules/ResourceOptimizer";
import TacticalRoutingEngine from "@/components/modules/TacticalRouting";

export default function OperationsPage() {
  return (
    <div className="flex flex-col gap-8 pb-12">
      <ResourceRecommender />
      <div className="px-6 border-t border-slate-800 pt-8 mt-4">
        <TacticalRoutingEngine />
      </div>
    </div>
  );
}
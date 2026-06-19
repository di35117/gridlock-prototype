import DataFoundationHub from "@/components/modules/DataFoundation";
import OSINTHarvester from "@/components/modules/OsintHarvester";
import CctvIngestion from "@/components/modules/CctvIngestion";

export default function IntelligencePage() {
  return (
    <div className="flex flex-col gap-8 pb-12">
      <DataFoundationHub />
      <div className="px-6 border-t border-slate-800 pt-8 mt-4">
        <OSINTHarvester />
      </div>
      <div className="px-6 border-t border-slate-800 pt-8 mt-4">
        <CctvIngestion />
      </div>
    </div>
  );
}
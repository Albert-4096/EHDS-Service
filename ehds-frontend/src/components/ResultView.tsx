import { useState } from 'react';
import JsonView from '@uiw/react-json-view';
import { darkTheme } from '@uiw/react-json-view/dark';
import { motion } from 'framer-motion';
import { Download, CheckCircle, AlertTriangle, LayoutDashboard, Code2, RotateCcw } from 'lucide-react';
import { FHIRSummaryPanel } from './FHIRSummaryPanel';

interface ResultViewProps {
  bundleData: any;
  onReset: () => void;
  isAnonymized: boolean;
}

type Tab = 'summary' | 'raw';

export function ResultView({ bundleData, onReset, isAnonymized }: ResultViewProps) {
  const [activeTab, setActiveTab] = useState<Tab>('summary');

  const handleDownload = () => {
    const dataStr =
      'data:text/json;charset=utf-8,' + encodeURIComponent(JSON.stringify(bundleData, null, 2));
    const a = document.createElement('a');
    a.setAttribute('href', dataStr);
    a.setAttribute('download', `fhir_bundle_${Date.now()}.json`);
    document.body.appendChild(a);
    a.click();
    a.remove();
  };

  const resourceCount = bundleData?.entry?.length ?? 0;

  return (
    <div className="w-full max-w-5xl mx-auto mt-6 mb-20">
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4 }}
        className="space-y-4"
      >
        {/* Header bar */}
        <div className="glass-panel p-5 rounded-2xl border border-green-500/25 bg-green-500/5">
          <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-full bg-green-500/15 flex items-center justify-center shrink-0">
                <CheckCircle className="text-green-400" size={20} />
              </div>
              <div>
                <h2 className="text-lg font-bold text-white leading-tight">Extraction Complete</h2>
                <p className="text-slate-400 text-sm mt-0.5">
                  {resourceCount} FHIR resources assembled ·{' '}
                  {isAnonymized ? 'Pillar 2 — Anonymized' : 'Pillar 1 — Direct Care'}
                </p>
              </div>
            </div>
            <div className="flex gap-2 shrink-0">
              <button
                onClick={handleDownload}
                className="flex items-center gap-2 px-3.5 py-2 bg-slate-800 hover:bg-slate-700 text-white rounded-lg transition-colors border border-slate-600 text-sm font-medium"
              >
                <Download size={15} />
                Export JSON
              </button>
              <button
                onClick={onReset}
                className="flex items-center gap-2 px-3.5 py-2 bg-blue-600 hover:bg-blue-500 text-white rounded-lg transition-colors text-sm font-medium"
              >
                <RotateCcw size={15} />
                New Document
              </button>
            </div>
          </div>
        </div>

        {/* Anonymization notice */}
        {isAnonymized && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            className="bg-teal-900/25 border border-teal-500/40 p-4 rounded-xl flex items-start gap-3"
          >
            <AlertTriangle className="text-teal-400 mt-0.5 shrink-0" size={18} />
            <div>
              <h4 className="font-semibold text-teal-300 text-sm">
                EHDS Pillar 2 Anonymization Applied
              </h4>
              <p className="text-xs text-teal-100/60 mt-0.5 leading-relaxed">
                Temporal dates shifted (Δt), PII identifiers obfuscated, rare diagnoses generalized
                to parent SNOMED concepts for k-anonymity — compliant with EHDS Regulation 2025/327.
              </p>
            </div>
          </motion.div>
        )}

        {/* Tab switcher */}
        <div className="flex items-center gap-1 bg-slate-800/50 p-1 rounded-xl border border-slate-700/50 w-fit">
          <TabBtn
            active={activeTab === 'summary'}
            onClick={() => setActiveTab('summary')}
            icon={<LayoutDashboard size={14} />}
            label="Clinical Summary"
          />
          <TabBtn
            active={activeTab === 'raw'}
            onClick={() => setActiveTab('raw')}
            icon={<Code2 size={14} />}
            label="Raw FHIR Bundle"
          />
        </div>

        {/* Panel */}
        {activeTab === 'summary' ? (
          <FHIRSummaryPanel bundle={bundleData} />
        ) : (
          <div className="glass-panel rounded-2xl overflow-hidden border border-slate-700/60">
            <div className="bg-[#141920] p-4 h-[640px] overflow-y-auto custom-scrollbar">
              <JsonView
                value={bundleData}
                collapsed={2}
                displayDataTypes={false}
                displayObjectSize={false}
                enableClipboard={true}
                style={{ ...darkTheme, backgroundColor: 'transparent', fontSize: 13 }}
              />
            </div>
          </div>
        )}
      </motion.div>
    </div>
  );
}

function TabBtn({
  active, onClick, icon, label,
}: {
  active: boolean; onClick: () => void; icon: React.ReactNode; label: string;
}) {
  return (
    <button
      onClick={onClick}
      className={`flex items-center gap-1.5 px-4 py-2 rounded-lg text-sm font-medium transition-all ${
        active ? 'bg-slate-700 text-white shadow' : 'text-slate-400 hover:text-white'
      }`}
    >
      {icon}
      {label}
    </button>
  );
}

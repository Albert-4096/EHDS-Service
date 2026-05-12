import JsonView from '@uiw/react-json-view';
import { darkTheme } from '@uiw/react-json-view/dark';
import { motion } from 'framer-motion';
import { Download, CheckCircle, AlertTriangle } from 'lucide-react';

interface ResultViewProps {
  bundleData: any;
  onReset: () => void;
  isAnonymized: boolean;
}

export function ResultView({ bundleData, onReset, isAnonymized }: ResultViewProps) {
  
  const handleDownload = () => {
    const dataStr = "data:text/json;charset=utf-8," + encodeURIComponent(JSON.stringify(bundleData, null, 2));
    const downloadAnchorNode = document.createElement('a');
    downloadAnchorNode.setAttribute("href", dataStr);
    downloadAnchorNode.setAttribute("download", `fhir_bundle_${Date.now()}.json`);
    document.body.appendChild(downloadAnchorNode); // required for firefox
    downloadAnchorNode.click();
    downloadAnchorNode.remove();
  };

  return (
    <div className="w-full max-w-5xl mx-auto mt-8 mb-20 flex flex-col">
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="glass-panel p-6 rounded-2xl w-full border border-slate-700"
      >
        <div className="flex flex-col md:flex-row justify-between items-start md:items-center mb-6 border-b border-slate-700 pb-4">
          <div>
            <h2 className="text-2xl font-bold flex items-center gap-2">
              <CheckCircle className="text-green-500" />
              Extraction Complete
            </h2>
            <p className="text-slate-400 mt-1">
              {isAnonymized 
                ? "Pillar 2 Secondary Use - Patient data has been fully anonymized and redacted." 
                : "Pillar 1 Primary Use - Direct Care Record"}
            </p>
          </div>
          
          <div className="flex gap-4 mt-4 md:mt-0">
            <button
              onClick={handleDownload}
              className="flex items-center gap-2 px-4 py-2 bg-slate-800 hover:bg-slate-700 text-white rounded-lg transition-colors border border-slate-600"
            >
              <Download size={18} />
              Export JSON
            </button>
            <button
              onClick={onReset}
              className="px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white rounded-lg transition-colors"
            >
              Upload Another
            </button>
          </div>
        </div>

        {isAnonymized && (
          <div className="mb-6 bg-teal-900/30 border border-teal-500/50 p-4 rounded-lg flex items-start gap-3">
            <AlertTriangle className="text-teal-400 mt-0.5" size={20} />
            <div>
              <h4 className="font-semibold text-teal-300">Anonymization Applied</h4>
              <p className="text-sm text-teal-100/70">
                The timeline dates have been deterministically shifted and explicit PII identifiers (CNP, names) have been obfuscated in compliance with EHDS regulations.
              </p>
            </div>
          </div>
        )}

        <div className="bg-[#1e1e1e] rounded-xl overflow-hidden p-4 h-[600px] overflow-y-auto custom-scrollbar">
          <JsonView
            value={bundleData}
            collapsed={2}
            displayDataTypes={false}
            displayObjectSize={false}
            enableClipboard={true}
            style={{ ...darkTheme, backgroundColor: 'transparent', fontSize: 13 }}
          />
        </div>
      </motion.div>
    </div>
  );
}

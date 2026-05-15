import { useState } from 'react';
import axios from 'axios';
import { UploadDropzone } from './components/UploadDropzone';
import { LoadingScreen } from './components/LoadingScreen';
import { ResultView } from './components/ResultView';
import { AnimatedBackground } from './components/AnimatedBackground';
import { ShieldCheck, Globe } from 'lucide-react';

const API_BASE_URL = import.meta.env.VITE_API_URL || '/api/v1';

type AppState = 'upload' | 'loading' | 'result' | 'error';

function App() {
  const [appState, setAppState] = useState<AppState>('upload');
  const [bundleData, setBundleData] = useState<any>(null);
  const [errorMessage, setErrorMessage] = useState<string>('');
  const [isAnonymized, setIsAnonymized] = useState(false);

  const handleFileSelect = async (file: File, usePillar2: boolean) => {
    setIsAnonymized(usePillar2);
    setAppState('loading');
    setErrorMessage('');

    const formData = new FormData();
    formData.append('file', file);
    const endpoint = usePillar2 ? '/extract/secondary' : '/extract/primary';

    try {
      const response = await axios.post(`${API_BASE_URL}${endpoint}`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
        timeout: 120000,
      });
      setBundleData(response.data);
      setAppState('result');
    } catch (error: any) {
      console.error(error);
      setErrorMessage(
        error.response?.data?.detail || error.message || 'An unknown error occurred.'
      );
      setAppState('error');
    }
  };

  const resetApp = () => {
    setAppState('upload');
    setBundleData(null);
    setErrorMessage('');
  };

  return (
    <div className="min-h-screen bg-[#0a0f1e] text-slate-100 font-sans selection:bg-teal-500/30">
      {/* Canvas background — fixed, behind everything */}
      <AnimatedBackground />

      {/* Nav */}
      <nav className="border-b border-slate-800/60 bg-[#0a0f1e]/80 backdrop-blur-md sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-14 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-blue-500 to-teal-400 flex items-center justify-center shadow-lg shadow-blue-500/20">
              <span className="font-bold text-white text-base leading-none">+</span>
            </div>
            <span className="text-lg font-semibold tracking-tight">
              EHDS<span className="text-teal-400">.</span>Pipeline
            </span>
          </div>

          <div className="flex items-center gap-2">
            <Badge icon={<ShieldCheck size={11} />} label="EHDS 2025/327" color="blue" />
            <Badge icon={<Globe size={11} />} label="HL7 FHIR R4" color="teal" />
            <span className="hidden sm:block text-xs text-slate-600 border border-slate-700/60 px-2 py-1 rounded-full font-mono">
              EEHRxF Ready
            </span>
          </div>
        </div>
      </nav>

      {/* Main content — above canvas */}
      <main className="relative z-10 px-4 pb-12">
        {appState === 'upload' && (
          <UploadDropzone onFileSelect={handleFileSelect} />
        )}

        {appState === 'result' && (
          <ResultView
            bundleData={bundleData}
            onReset={resetApp}
            isAnonymized={isAnonymized}
          />
        )}

        {appState === 'error' && (
          <div className="max-w-2xl mx-auto mt-20 text-center">
            <div className="glass-panel p-8 rounded-2xl border border-red-500/30 bg-red-500/5">
              <div className="w-12 h-12 rounded-full bg-red-500/20 flex items-center justify-center mx-auto mb-4">
                <span className="text-red-400 text-2xl">✕</span>
              </div>
              <h2 className="text-xl font-bold text-red-400 mb-3">Processing Failed</h2>
              <p className="text-slate-300 text-sm mb-6 leading-relaxed">{errorMessage}</p>
              <button
                onClick={resetApp}
                className="px-6 py-2.5 bg-slate-800 hover:bg-slate-700 text-white rounded-lg transition-colors border border-slate-600 text-sm font-medium"
              >
                Try Again
              </button>
            </div>
          </div>
        )}
      </main>

      {/* Loading overlay — fixed fullscreen, rendered outside main */}
      {appState === 'loading' && <LoadingScreen />}
    </div>
  );
}

function Badge({ icon, label, color }: { icon: React.ReactNode; label: string; color: 'blue' | 'teal' }) {
  const colors = {
    blue: 'text-blue-400 border-blue-500/30 bg-blue-500/10',
    teal: 'text-teal-400 border-teal-500/30 bg-teal-500/10',
  };
  return (
    <span className={`hidden sm:flex items-center gap-1 text-xs border px-2 py-1 rounded-full font-medium ${colors[color]}`}>
      {icon}
      {label}
    </span>
  );
}

export default App;

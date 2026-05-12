import { useState } from 'react';
import axios from 'axios';
import { UploadDropzone } from './components/UploadDropzone';
import { LoadingScreen } from './components/LoadingScreen';
import { ResultView } from './components/ResultView';

// Use relative path for reverse proxy by default.
// This allows Nginx to intercept /api/v1 and route it to the backend container securely.
const API_BASE_URL = import.meta.env.VITE_API_URL || "/api/v1";

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
      // Increase timeout because LLM and OCR take time (1-2 mins max)
      const response = await axios.post(`${API_BASE_URL}${endpoint}`, formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
        timeout: 120000 
      });

      setBundleData(response.data);
      setAppState('result');
    } catch (error: any) {
      console.error(error);
      setErrorMessage(error.response?.data?.detail || error.message || 'An unknown error occurred during extraction.');
      setAppState('error');
    }
  };

  const resetApp = () => {
    setAppState('upload');
    setBundleData(null);
    setErrorMessage('');
  };

  return (
    <div className="min-h-screen bg-slate-900 text-slate-100 font-sans selection:bg-teal-500/30">
      <nav className="border-b border-slate-800 bg-slate-900/50 backdrop-blur-md sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-teal-400 to-blue-500 flex items-center justify-center shadow-lg shadow-teal-500/20">
              <span className="font-bold text-slate-900 text-xl">+</span>
            </div>
            <span className="text-xl font-semibold tracking-tight">EHDS<span className="text-teal-400">.</span>Platform</span>
          </div>
        </div>
      </nav>

      <main className="px-4 py-8">
        {appState === 'upload' && (
          <UploadDropzone onFileSelect={handleFileSelect} />
        )}

        {appState === 'loading' && (
          <LoadingScreen />
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
            <div className="glass-panel p-8 rounded-2xl border-red-500/30 bg-red-500/10">
              <h2 className="text-2xl font-bold text-red-400 mb-4">Processing Failed</h2>
              <p className="text-slate-300 mb-6">{errorMessage}</p>
              <button
                onClick={resetApp}
                className="px-6 py-3 bg-slate-800 hover:bg-slate-700 text-white rounded-lg transition-colors border border-slate-600"
              >
                Try Again
              </button>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}

export default App;

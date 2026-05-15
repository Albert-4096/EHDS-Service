import { useState } from 'react';
import axios from 'axios';
import { UploadDropzone } from './components/UploadDropzone';
import { LoadingScreen } from './components/LoadingScreen';
import { ResultView } from './components/ResultView';

const API_BASE_URL = import.meta.env.VITE_API_URL || '/api/v1';

const BLUE   = '#0F2A4A';
const ACCENT = '#3A7BD5';
const MUTED  = '#5B6878';
const BORDER = '#E5E9F0';
const TEXT   = '#1A2433';

type AppState = 'upload' | 'loading' | 'result' | 'error';

function TopBar({ step }: { step: AppState }) {
  const crumbs =
    step === 'upload'  ? ['Conversions', 'New upload'] :
    step === 'loading' ? ['Conversions', 'Processing…'] :
    step === 'error'   ? ['Conversions', 'Error'] :
                         ['Conversions', 'Result'];

  return (
    <div style={{
      height: 56,
      background: '#fff',
      borderBottom: `1px solid ${BORDER}`,
      display: 'flex',
      alignItems: 'center',
      padding: '0 28px',
      gap: 24,
      flexShrink: 0,
      position: 'sticky',
      top: 0,
      zIndex: 50,
    }}>
      {/* Brand */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 10, fontWeight: 600, color: BLUE, fontSize: 15, letterSpacing: -0.2, flexShrink: 0 }}>
        <div style={{
          width: 26, height: 26, borderRadius: 6, background: BLUE, color: '#fff',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          fontFamily: '"IBM Plex Mono", monospace', fontSize: 11, fontWeight: 700,
        }}>EP</div>
        <span>EHDS Platform</span>
      </div>

      {/* Breadcrumb */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 13, color: MUTED }}>
        {crumbs.map((c, i) => (
          <span key={i} style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            {i > 0 && <span style={{ opacity: 0.4 }}>/</span>}
            <span style={i === crumbs.length - 1 ? { color: TEXT, fontWeight: 500 } : undefined}>{c}</span>
          </span>
        ))}
      </div>

      {/* Right side badges */}
      <div style={{ marginLeft: 'auto', display: 'flex', alignItems: 'center', gap: 10, fontSize: 12 }}>
        <span style={{ color: MUTED, border: `1px solid ${BORDER}`, borderRadius: 20, padding: '3px 10px', fontFamily: '"IBM Plex Mono", monospace' }}>EHDS 2025/327</span>
        <span style={{ color: ACCENT, border: `1px solid #C9D4E2`, borderRadius: 20, padding: '3px 10px', fontFamily: '"IBM Plex Mono", monospace' }}>HL7 FHIR R4</span>
      </div>
    </div>
  );
}

function App() {
  const [appState, setAppState] = useState<AppState>('upload');
  const [bundleData, setBundleData] = useState<any>(null);
  const [errorMessage, setErrorMessage] = useState<string>('');
  const [isAnonymized, setIsAnonymized] = useState(false);
  const [uploadedFile, setUploadedFile] = useState<File | null>(null);

  const handleFileSelect = async (file: File, usePillar2: boolean) => {
    setIsAnonymized(usePillar2);
    setUploadedFile(file);
    setAppState('loading');
    setErrorMessage('');

    const formData = new FormData();
    formData.append('file', file);
    const endpoint = usePillar2 ? '/extract/secondary' : '/extract/primary';

    try {
      const response = await axios.post(`${API_BASE_URL}${endpoint}`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
        timeout: 300000,
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
    setUploadedFile(null);
  };

  return (
    <div style={{ minHeight: '100vh', background: '#F5F7FA', fontFamily: '"Inter", -apple-system, sans-serif', color: TEXT, display: 'flex', flexDirection: 'column' }}>
      <TopBar step={appState} />

      <main style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
        {appState === 'upload' && (
          <UploadDropzone onFileSelect={handleFileSelect} />
        )}

        {appState === 'loading' && (
          <LoadingScreen fileName={uploadedFile?.name} />
        )}

        {appState === 'result' && (
          <ResultView
            bundleData={bundleData}
            onReset={resetApp}
            isAnonymized={isAnonymized}
            originalFile={uploadedFile}
          />
        )}

        {appState === 'error' && (
          <div style={{ maxWidth: 560, margin: '80px auto', padding: '0 24px' }}>
            <div style={{
              background: '#fff',
              border: `1px solid #F5C6C3`,
              borderRadius: 12,
              padding: 32,
              textAlign: 'center',
            }}>
              <div style={{
                width: 48, height: 48, borderRadius: 24, background: '#FDECEA',
                display: 'flex', alignItems: 'center', justifyContent: 'center', margin: '0 auto 16px',
              }}>
                <span style={{ color: '#C03A2B', fontSize: 22, fontWeight: 700 }}>✕</span>
              </div>
              <h2 style={{ margin: '0 0 8px', fontSize: 20, fontWeight: 600, color: '#C03A2B' }}>Processing Failed</h2>
              <p style={{ color: MUTED, fontSize: 14, lineHeight: 1.6, margin: '0 0 24px' }}>{errorMessage}</p>
              <button
                onClick={resetApp}
                style={{
                  padding: '10px 24px', background: BLUE, color: '#fff',
                  border: 'none', borderRadius: 6, cursor: 'pointer',
                  fontFamily: 'inherit', fontSize: 14, fontWeight: 500,
                }}
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

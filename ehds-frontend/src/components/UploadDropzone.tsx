import React, { useCallback, useState } from 'react';
import { ShieldCheck, Lock } from 'lucide-react';

const BLUE   = '#0F2A4A';
const ACCENT = '#3A7BD5';
const BG     = '#F5F7FA';
const BORDER = '#E5E9F0';
const TEXT   = '#1A2433';
const MUTED  = '#5B6878';
const OK     = '#0E8559';

interface UploadDropzoneProps {
  onFileSelect: (file: File, isAnonymized: boolean) => void;
}

export function UploadDropzone({ onFileSelect }: UploadDropzoneProps) {
  const [isDragActive, setIsDragActive] = useState(false);
  const [usePillar2, setUsePillar2] = useState(false);
  const [sampleLoading, setSampleLoading] = useState(false);

  const handleSampleClick = async () => {
    if (sampleLoading) return;
    setSampleLoading(true);
    try {
      const resp = await fetch('scrisoare medicala_filled.pdf');
      const blob = await resp.blob();
      const file = new File([blob], 'scrisoare medicala_filled.pdf', { type: 'application/pdf' });
      onFileSelect(file, usePillar2);
    } catch (err) {
      console.error('Failed to load sample:', err);
    } finally {
      setSampleLoading(false);
    }
  };

  const handleDrag = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === 'dragenter' || e.type === 'dragover') setIsDragActive(true);
    else if (e.type === 'dragleave') setIsDragActive(false);
  }, []);

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      e.stopPropagation();
      setIsDragActive(false);
      if (e.dataTransfer.files?.[0]) {
        onFileSelect(e.dataTransfer.files[0], usePillar2);
      }
    },
    [onFileSelect, usePillar2]
  );

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    e.preventDefault();
    if (e.target.files?.[0]) onFileSelect(e.target.files[0], usePillar2);
  };

  return (
    <div style={{ flex: 1, padding: '40px 56px', overflow: 'auto', animation: 'afade-in .4s ease' }}>
      <div style={{ maxWidth: 880, margin: '0 auto' }}>

        {/* Header */}
        <div style={{ marginBottom: 8, fontSize: 12, letterSpacing: 1.5, color: MUTED, textTransform: 'uppercase', fontWeight: 600 }}>New conversion</div>
        <h1 style={{ margin: 0, fontSize: 32, fontWeight: 600, letterSpacing: -0.6, color: BLUE }}>Upload a discharge report</h1>
        <p style={{ marginTop: 10, color: MUTED, fontSize: 15, lineHeight: 1.55, maxWidth: 640 }}>
          We'll convert your hospital discharge document to a compliant{' '}
          <strong style={{ color: TEXT, fontWeight: 600 }}>FHIR R4 bundle</strong> (US Core / EHDS 2025/327).
          Processing typically takes 10–30 seconds per document.
        </p>

        {/* Pillar toggle */}
        <div style={{ marginTop: 24, display: 'inline-flex', alignItems: 'center', gap: 2, background: '#EAECF0', padding: 3, borderRadius: 8, border: `1px solid ${BORDER}` }}>
          <PillarBtn
            active={!usePillar2}
            onClick={() => setUsePillar2(false)}
            icon={<ShieldCheck size={13} />}
            label="Pillar 1 — Direct Care"
          />
          <PillarBtn
            active={usePillar2}
            onClick={() => setUsePillar2(true)}
            icon={<Lock size={13} />}
            label="Pillar 2 — Anonymized"
            isP2
          />
        </div>
        <p style={{ marginTop: 8, fontSize: 12, color: MUTED }}>
          {usePillar2
            ? 'Temporal shifting (Δt) + PII stripping + k-anonymity generalization for research use'
            : 'Full-fidelity record for authorized healthcare professionals in direct patient care'}
        </p>

        {/* Drop zone */}
        <div
          onDragEnter={handleDrag}
          onDragLeave={handleDrag}
          onDragOver={handleDrag}
          onDrop={handleDrop}
          style={{
            marginTop: 28,
            position: 'relative',
            background: isDragActive ? 'rgba(255,255,255,0.92)' : 'rgba(250,251,253,0.65)',
            backdropFilter: 'blur(10px)',
            WebkitBackdropFilter: 'blur(10px)',
            border: `2px dashed ${isDragActive ? ACCENT : '#C9D4E2'}`,
            borderRadius: 10,
            padding: '56px 40px',
            textAlign: 'center',
            cursor: 'pointer',
            transition: 'all .15s',
            boxShadow: isDragActive ? `0 0 0 4px rgba(58,123,213,.1)` : 'none',
          }}
        >
          <input
            type="file"
            accept=".pdf,.doc,.docx,.txt"
            style={{ position: 'absolute', inset: 0, opacity: 0, cursor: 'pointer', width: '100%', height: '100%' }}
            onChange={handleChange}
          />
          <div style={{
            width: 56, height: 56, margin: '0 auto 16px',
            borderRadius: 14,
            background: isDragActive ? BLUE : '#E8EEF6',
            color: isDragActive ? '#fff' : BLUE,
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            transition: 'all .15s',
          }}>
            <svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M12 4v12m0-12l-5 5m5-5l5 5M4 20h16"/>
            </svg>
          </div>
          <div style={{ fontSize: 17, fontWeight: 600, color: TEXT }}>
            {isDragActive ? 'Drop file here' : 'Drop a discharge report here'}
          </div>
          <div style={{ marginTop: 6, color: MUTED, fontSize: 14 }}>
            or <span style={{ color: ACCENT, fontWeight: 500, textDecoration: 'underline' }}>browse your computer</span>
          </div>
          <div style={{ marginTop: 22, display: 'flex', gap: 8, justifyContent: 'center', flexWrap: 'wrap' }}>
            {['PDF', 'DOCX', 'HL7 v2', 'CDA', 'TXT'].map((t) => (
              <span key={t} style={{
                fontFamily: '"IBM Plex Mono", monospace', fontSize: 11,
                padding: '3px 9px', background: '#fff', border: `1px solid ${BORDER}`,
                borderRadius: 4, color: MUTED,
              }}>{t}</span>
            ))}
          </div>
          <div style={{ marginTop: 14, fontSize: 12, color: MUTED }}>
            Max 25 MB · End-to-end encrypted · HIPAA-compliant
          </div>
        </div>

        {/* Sample documents */}
        <div style={{ marginTop: 28, display: 'flex', alignItems: 'center', gap: 14 }}>
          <div style={{ flex: 1, height: 1, background: BORDER }} />
          <span style={{ fontSize: 12, color: MUTED, textTransform: 'uppercase', letterSpacing: 1.2 }}>or try a sample</span>
          <div style={{ flex: 1, height: 1, background: BORDER }} />
        </div>

        <div style={{ marginTop: 20 }}>
          <button
            onClick={handleSampleClick}
            disabled={sampleLoading}
            style={{
              width: '100%', textAlign: 'left', padding: '14px 16px',
              background: 'rgba(255,255,255,0.75)',
              backdropFilter: 'blur(8px)',
              WebkitBackdropFilter: 'blur(8px)',
              border: `1px solid ${BORDER}`, borderRadius: 8,
              cursor: sampleLoading ? 'wait' : 'pointer',
              display: 'flex', alignItems: 'center', gap: 14,
              fontFamily: 'inherit', opacity: sampleLoading ? 0.7 : 1, transition: 'opacity .15s',
            }}
          >
            <div style={{ width: 36, height: 44, background: BG, borderRadius: 3, display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>
              <svg width="18" height="22" viewBox="0 0 18 22" fill="none">
                <rect x="0.5" y="0.5" width="17" height="21" rx="1.5" fill="#fff" stroke="#C9D4E2"/>
                <path d="M4 6h10M4 10h10M4 14h7" stroke={MUTED} strokeWidth="1"/>
              </svg>
            </div>
            <div style={{ minWidth: 0, flex: 1 }}>
              <div style={{ fontSize: 14, fontWeight: 500, color: TEXT }}>Scrisoare Medicală</div>
              <div style={{ fontSize: 12, color: MUTED, marginTop: 2 }}>Romanian medical letter · Bilet de Externare</div>
            </div>
            {sampleLoading ? (
              <div style={{ width: 16, height: 16, borderRadius: 8, border: `2px solid ${ACCENT}`, borderTopColor: 'transparent', animation: 'aspin .8s linear infinite', flexShrink: 0 }} />
            ) : (
              <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke={ACCENT} strokeWidth="1.8" strokeLinecap="round" style={{ flexShrink: 0 }}>
                <path d="M6 4l4 4-4 4"/>
              </svg>
            )}
          </button>
        </div>

        {/* Compliance footer */}
        <div style={{
          marginTop: 28, padding: '14px 18px',
          background: 'rgba(255,255,255,0.75)',
          backdropFilter: 'blur(8px)',
          WebkitBackdropFilter: 'blur(8px)',
          border: `1px solid ${BORDER}`, borderRadius: 8,
          display: 'flex', alignItems: 'center', gap: 12, fontSize: 13, color: MUTED,
        }}>
          <svg width="18" height="18" viewBox="0 0 18 18" fill="none" stroke={OK} strokeWidth="1.8">
            <path d="M9 1l7 4v5c0 4-3.5 6.5-7 7-3.5-.5-7-3-7-7V5l7-4z"/>
            <path d="M5.5 9l2.5 2.5L12.5 7"/>
          </svg>
          <span>
            <strong style={{ color: TEXT, fontWeight: 600 }}>Compliance:</strong>{' '}
            EHDS 2025/327 · HIPAA · GDPR · HL7 FHIR R4 · Bundles signed under audit trail
          </span>
        </div>

        {/* Pipeline stages strip */}
        <div style={{ marginTop: 28, display: 'flex', alignItems: 'center', gap: 6, flexWrap: 'wrap' }}>
          {PIPELINE_STAGES.map((stage, i) => (
            <React.Fragment key={stage}>
              <span style={{ fontSize: 11, color: MUTED, fontFamily: '"IBM Plex Mono", monospace', background: '#EAECF0', padding: '3px 8px', borderRadius: 4 }}>{stage}</span>
              {i < PIPELINE_STAGES.length - 1 && (
                <span style={{ color: '#C9D4E2', fontSize: 11 }}>›</span>
              )}
            </React.Fragment>
          ))}
        </div>
      </div>
    </div>
  );
}

const PIPELINE_STAGES = [
  'PDF Forensics', 'Text Extract', 'Classify', 'Zone Detect',
  'Structured Fields', 'Labs', 'LLM Epicriza', 'Medications', 'FHIR Assembly', 'Bundle',
];

function PillarBtn({
  active, onClick, icon, label, isP2,
}: {
  active: boolean; onClick: () => void; icon: React.ReactNode; label: string; isP2?: boolean;
}) {
  const activeBg = isP2 ? '#0D6E5A' : BLUE;
  return (
    <button
      onClick={onClick}
      style={{
        display: 'flex', alignItems: 'center', gap: 7,
        padding: '7px 14px', borderRadius: 6, border: 'none',
        background: active ? activeBg : 'transparent',
        color: active ? '#fff' : MUTED,
        fontFamily: 'inherit', fontSize: 13, fontWeight: 500,
        cursor: 'pointer', transition: 'all .15s', whiteSpace: 'nowrap',
      }}
    >
      {icon}
      {label}
    </button>
  );
}

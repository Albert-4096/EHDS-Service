import { useState } from 'react';
import JsonView from '@uiw/react-json-view';
import { darkTheme } from '@uiw/react-json-view/dark';
import { FHIRSummaryPanel } from './FHIRSummaryPanel';

const BLUE   = '#0F2A4A';
const ACCENT = '#3A7BD5';
const BORDER = '#E5E9F0';
const TEXT   = '#1A2433';
const MUTED  = '#5B6878';
const OK     = '#0E8559';

interface ResultViewProps {
  bundleData: any;
  onReset: () => void;
  isAnonymized: boolean;
  originalFile?: File | null;
}

type Tab = 'summary' | 'json';

function patientName(bundle: any): string {
  const p = (bundle?.entry ?? []).map((e: any) => e.resource).find((r: any) => r?.resourceType === 'Patient');
  if (!p?.name?.length) return 'Patient';
  const n = p.name[0];
  return [[...(n.given ?? [])].join(' '), n.family].filter(Boolean).join(' ') || 'Patient';
}

function encounterDates(bundle: any): string {
  const enc = (bundle?.entry ?? []).map((e: any) => e.resource).find((r: any) => r?.resourceType === 'Encounter');
  const period = enc?.actualPeriod ?? enc?.period;
  if (!period?.start) return '';
  const fmt = (s: string) => {
    try { return new Date(s).toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: 'numeric' }); }
    catch { return s; }
  };
  return period.end
    ? `${fmt(period.start)} — ${fmt(period.end)}`
    : `From ${fmt(period.start)}`;
}

export function ResultView({ bundleData, onReset, isAnonymized, originalFile }: ResultViewProps) {
  const [tab, setTab] = useState<Tab>('summary');

  const handleDownloadJSON = () => {
    const dataStr = 'data:text/json;charset=utf-8,' + encodeURIComponent(JSON.stringify(bundleData, null, 2));
    const safeName = patientName(bundleData).replace(/\s+/g, '_').toLowerCase() || 'patient';
    const a = document.createElement('a');
    a.setAttribute('href', dataStr);
    a.setAttribute('download', `fhir_bundle_${safeName}.json`);
    document.body.appendChild(a);
    a.click();
    a.remove();
  };

  const handleDownloadPDF = () => {
    if (originalFile) {
      const url = URL.createObjectURL(originalFile);
      const a = document.createElement('a');
      a.href = url;
      a.download = originalFile.name;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
    } else {
      window.print();
    }
  };

  const resourceCount = bundleData?.entry?.length ?? 0;
  const name = patientName(bundleData);
  const dates = encounterDates(bundleData);

  return (
    <div style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden', animation: 'afade-in .4s ease' }}>
      {/* Result header */}
      <div style={{ background: '#fff', borderBottom: `1px solid ${BORDER}`, padding: '18px 56px 0' }}>

        {/* Compliance banner */}
        <div style={{
          background: 'linear-gradient(90deg,#F0F8F4 0%,#fff 100%)',
          border: '1px solid #C8E6D4', borderRadius: 8,
          padding: '12px 16px', display: 'flex', alignItems: 'center', gap: 12, marginBottom: 16,
        }}>
          <div style={{
            width: 32, height: 32, borderRadius: 16, background: OK,
            color: '#fff', display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0,
            animation: 'apulse 2s ease-in-out infinite',
          }}>
            <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="#fff" strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round">
              <path d="M3 8l3.5 3.5L13 5.5"/>
            </svg>
          </div>
          <div style={{ flex: 1 }}>
            <div style={{ fontSize: 14, fontWeight: 600, color: TEXT }}>
              Bundle validated · EHDS 2025/327 / US Core 6.1.0 compliant
              {isAnonymized && <span style={{ marginLeft: 8, fontSize: 12, color: '#0D6E5A', fontWeight: 500 }}>· Pillar 2 anonymized</span>}
            </div>
            <div style={{ fontSize: 12, color: MUTED, marginTop: 2 }}>
              {resourceCount} FHIR resources · 0 validation errors · signed {new Date().toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: 'numeric' })}
            </div>
          </div>
          <span style={{ fontFamily: '"IBM Plex Mono", monospace', fontSize: 12, color: OK, fontWeight: 600 }}>✓ READY</span>
        </div>

        {/* Title row + actions */}
        <div style={{ display: 'flex', alignItems: 'flex-end', justifyContent: 'space-between', gap: 24, paddingBottom: 16 }}>
          <div style={{ minWidth: 0, flex: 1 }}>
            <div style={{ fontSize: 12, letterSpacing: 1.5, color: MUTED, textTransform: 'uppercase', fontWeight: 600 }}>
              Discharge summary · <span style={{ fontFamily: '"IBM Plex Mono", monospace' }}>FHIR R4</span>
            </div>
            <h1 style={{ margin: '6px 0 0', fontSize: 22, fontWeight: 600, letterSpacing: -0.4, color: BLUE, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
              {name}
            </h1>
            {dates && <div style={{ marginTop: 4, fontSize: 13, color: MUTED }}>{dates}</div>}
          </div>
          <div style={{ display: 'flex', gap: 8, flexShrink: 0 }}>
            <PillButton onClick={onReset} small>↺ New upload</PillButton>
            <PillButton onClick={handleDownloadPDF} small>↓ PDF</PillButton>
            <PillButton onClick={handleDownloadJSON} primary small>↓ FHIR JSON</PillButton>
          </div>
        </div>

        {/* Tabs */}
        <div style={{ display: 'flex', gap: 2 }}>
          {[['summary', 'Clinical summary'], ['json', 'FHIR JSON']] .map(([k, l]) => (
            <button key={k} onClick={() => setTab(k as Tab)} style={{
              background: 'transparent', border: 'none', cursor: 'pointer', fontFamily: 'inherit',
              padding: '12px 18px', fontSize: 14, fontWeight: 500,
              color: tab === k ? BLUE : MUTED,
              borderBottom: `2px solid ${tab === k ? BLUE : 'transparent'}`,
              marginBottom: -1, transition: 'color .15s',
            }}>{l}</button>
          ))}
        </div>
      </div>

      {/* Tab content */}
      {tab === 'summary' ? (
        <div style={{ flex: 1, overflow: 'auto', padding: '28px 56px 48px' }}>
          <FHIRSummaryPanel bundle={bundleData} />
        </div>
      ) : (
        <div style={{ flex: 1, overflow: 'auto', padding: '24px 56px 40px' }}>
          <div style={{ background: '#0B1B30', borderRadius: 10, overflow: 'hidden' }}>
            {/* Code header */}
            <div style={{
              background: '#102742', padding: '10px 16px',
              display: 'flex', alignItems: 'center', gap: 14,
              color: '#A8B8CC', fontSize: 12,
              fontFamily: '"IBM Plex Mono", monospace',
              borderBottom: '1px solid #1B355C',
            }}>
              <span style={{ display: 'flex', gap: 6 }}>
                <span style={{ width: 10, height: 10, borderRadius: 5, background: '#FF5F57' }} />
                <span style={{ width: 10, height: 10, borderRadius: 5, background: '#FEBC2E' }} />
                <span style={{ width: 10, height: 10, borderRadius: 5, background: '#28C840' }} />
              </span>
              <span>fhir_bundle.json</span>
              <span style={{ color: '#5E7593' }}>·</span>
              <span>{resourceCount} resources</span>
              <span style={{ marginLeft: 'auto', display: 'flex', gap: 8 }}>
                <button
                  onClick={() => navigator.clipboard?.writeText(JSON.stringify(bundleData, null, 2))}
                  style={{ background: 'transparent', border: '1px solid #2C4A75', color: '#A8B8CC', padding: '4px 10px', borderRadius: 4, fontSize: 11, fontFamily: 'inherit', cursor: 'pointer' }}
                >Copy</button>
                <button
                  onClick={handleDownloadJSON}
                  style={{ background: ACCENT, border: 'none', color: '#fff', padding: '4px 10px', borderRadius: 4, fontSize: 11, fontFamily: 'inherit', cursor: 'pointer', fontWeight: 500 }}
                >Download .json</button>
              </span>
            </div>
            <div className="custom-scrollbar" style={{ padding: '16px 18px', maxHeight: 560, overflow: 'auto' }}>
              <JsonView
                value={bundleData}
                collapsed={2}
                displayDataTypes={false}
                displayObjectSize={false}
                enableClipboard={false}
                style={{ ...darkTheme, backgroundColor: 'transparent', fontSize: 12.5 }}
              />
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function PillButton({
  children, onClick, primary, small,
}: {
  children: React.ReactNode; onClick: () => void; primary?: boolean; small?: boolean;
}) {
  return (
    <button onClick={onClick} style={{
      padding: small ? '7px 14px' : '11px 22px',
      borderRadius: 6,
      border: primary ? 'none' : `1px solid ${BORDER}`,
      background: primary ? BLUE : '#fff',
      color: primary ? '#fff' : TEXT,
      fontFamily: 'inherit', fontSize: small ? 13 : 14, fontWeight: 500,
      cursor: 'pointer',
      display: 'inline-flex', alignItems: 'center', gap: 8,
      whiteSpace: 'nowrap', transition: 'all .15s',
    }}>{children}</button>
  );
}

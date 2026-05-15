import { useEffect, useState } from 'react';
import type { CSSProperties } from 'react';
import { motion, AnimatePresence } from 'framer-motion';

const STAGES = [
  { label: 'PDF Forensics',       sub: 'Detecting document type, page count, OCR requirement...',       ms: 1600 },
  { label: 'Text Extraction',     sub: 'pdfplumber + Tesseract OCR with Romanian language pack...',      ms: 2000 },
  { label: 'Classification',      sub: 'DOC_HDR vs DOC_BIS detection · zone anchor mapping...',          ms: 2200 },
  { label: 'Structured Fields',   sub: 'Demographics, dates, lab panels, checkbox groups...',            ms: 2800 },
  { label: 'LLM Epicriza',        sub: 'Claude AI parsing clinical narrative & patient history...',      ms: 7000 },
  { label: 'FHIR R4 Assembly',    sub: 'Building Patient, Encounter, Conditions, Medications...',        ms: 4500 },
  { label: 'Bundle Validation',   sub: 'HAPI FHIR validator · provenance hash · uploading...',           ms: 3000 },
];

// ── Ring component ──────────────────────────────────────────────────────────

interface RingProps {
  inset: number;
  borderColor: string;
  animName: string;
  duration: number;
  particleColor: string;
  particleSize: number;
  glowColor: string;
  /** second particle at bottom? */
  twin?: boolean;
}

function Ring({ inset, borderColor, animName, duration, particleColor, particleSize, glowColor, twin }: RingProps) {
  const ringStyle: CSSProperties = {
    position: 'absolute',
    inset,
    borderRadius: '50%',
    border: `1.5px solid ${borderColor}`,
    animation: `${animName} ${duration}s linear infinite`,
  };

  const dot = (side: 'top' | 'bottom'): CSSProperties => ({
    position: 'absolute',
    [side]: -(particleSize / 2),
    left: '50%',
    transform: 'translateX(-50%)',
    width: particleSize,
    height: particleSize,
    borderRadius: '50%',
    background: particleColor,
    boxShadow: `0 0 ${particleSize * 2.5}px ${particleSize}px ${glowColor}`,
    animation: 'particle-glow 1.8s ease-in-out infinite',
  });

  return (
    <div style={ringStyle}>
      <div style={dot('top')} />
      {twin && (
        <div style={{ ...dot('bottom'), opacity: 0.5, animationDelay: '0.9s' }} />
      )}
    </div>
  );
}

// ── Main component ──────────────────────────────────────────────────────────

export function LoadingScreen() {
  const [idx, setIdx] = useState(0);

  useEffect(() => {
    let current = 0;
    const advance = () => {
      if (current < STAGES.length - 1) {
        current++;
        setIdx(current);
        setTimeout(advance, STAGES[current].ms);
      }
    };
    const t = setTimeout(advance, STAGES[0].ms);
    return () => clearTimeout(t);
  }, []);

  const pct = Math.round(((idx + 1) / STAGES.length) * 100);

  return (
    <div
      className="fixed inset-0 z-40 flex flex-col items-center justify-center"
      style={{ background: 'rgba(10,15,30,0.82)', backdropFilter: 'blur(6px)' }}
    >
      {/* ── Atom ───────────────────────────────────────────────── */}
      <div
        style={{
          position: 'relative',
          width: 260,
          height: 260,
          perspective: '900px',
          perspectiveOrigin: '50% 50%',
        }}
      >
        {/* 3-D preserve group */}
        <div style={{ position: 'absolute', inset: 0, transformStyle: 'preserve-3d' }}>
          <Ring
            inset={16}
            borderColor="rgba(59,130,246,0.5)"
            animName="ring1-orbit"
            duration={4}
            particleColor="#60a5fa"
            particleSize={11}
            glowColor="rgba(96,165,250,0.65)"
            twin
          />
          <Ring
            inset={28}
            borderColor="rgba(20,184,166,0.45)"
            animName="ring2-orbit"
            duration={3.2}
            particleColor="#34d399"
            particleSize={9}
            glowColor="rgba(52,211,153,0.65)"
          />
          <Ring
            inset={42}
            borderColor="rgba(139,92,246,0.4)"
            animName="ring3-orbit"
            duration={5.8}
            particleColor="#a78bfa"
            particleSize={7}
            glowColor="rgba(167,139,250,0.65)"
          />
        </div>

        {/* Center (flat, above 3-D context) */}
        <div
          style={{
            position: 'absolute', inset: 0,
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            zIndex: 2,
          }}
        >
          {/* Sonar halos */}
          {[0, 1].map(i => (
            <div
              key={i}
              style={{
                position: 'absolute',
                width: 56, height: 56,
                borderRadius: '50%',
                border: '2px solid rgba(59,130,246,0.35)',
                animation: `halo-expand 2.2s ease-out infinite`,
                animationDelay: `${i * 1.1}s`,
              }}
            />
          ))}

          {/* Core sphere */}
          <div
            style={{
              width: 50, height: 50,
              borderRadius: '50%',
              background: 'linear-gradient(135deg, #1d4ed8 0%, #0d9488 100%)',
              animation: 'core-glow 2.6s ease-in-out infinite',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              position: 'relative', zIndex: 3,
              border: '2px solid rgba(255,255,255,0.15)',
            }}
          >
            <span style={{ color: 'white', fontWeight: 700, fontSize: 22, lineHeight: 1 }}>+</span>
          </div>
        </div>
      </div>

      {/* ── Stage text ─────────────────────────────────────────── */}
      <div className="mt-10 text-center" style={{ minHeight: 90 }}>
        <AnimatePresence mode="wait">
          <motion.div
            key={idx}
            initial={{ opacity: 0, y: 14 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -14 }}
            transition={{ duration: 0.35, ease: 'easeOut' }}
          >
            <p className="text-xs font-semibold tracking-widest uppercase mb-2"
               style={{ color: '#60a5fa', letterSpacing: '0.12em' }}>
              Stage {idx + 1} / {STAGES.length}
            </p>
            <h2 className="text-2xl font-bold text-white mb-2">{STAGES[idx].label}</h2>
            <p className="text-sm text-slate-400 max-w-xs mx-auto leading-relaxed">{STAGES[idx].sub}</p>
          </motion.div>
        </AnimatePresence>
      </div>

      {/* ── Progress bar ───────────────────────────────────────── */}
      <div className="mt-8" style={{ width: 280 }}>
        <div className="flex justify-between text-xs text-slate-500 mb-2">
          <span>Processing pipeline</span>
          <motion.span
            key={pct}
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="text-blue-400 font-mono font-semibold"
          >
            {pct}%
          </motion.span>
        </div>
        <div className="h-1.5 rounded-full overflow-hidden" style={{ background: 'rgba(255,255,255,0.06)' }}>
          <motion.div
            className="h-full rounded-full"
            style={{ background: 'linear-gradient(90deg, #3b82f6, #14b8a6)' }}
            initial={{ width: 0 }}
            animate={{ width: `${pct}%` }}
            transition={{ duration: 0.7, ease: 'easeOut' }}
          />
        </div>
      </div>

      {/* ── Stage dots ─────────────────────────────────────────── */}
      <div className="flex gap-2 mt-6">
        {STAGES.map((_, i) => (
          <motion.div
            key={i}
            animate={{
              width: i === idx ? 24 : i < idx ? 16 : 6,
              backgroundColor: i === idx ? '#60a5fa' : i < idx ? '#34d399' : 'rgba(255,255,255,0.12)',
            }}
            transition={{ duration: 0.4 }}
            style={{ height: 6, borderRadius: 3 }}
          />
        ))}
      </div>
    </div>
  );
}

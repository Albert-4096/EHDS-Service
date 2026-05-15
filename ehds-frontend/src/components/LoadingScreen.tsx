import { useEffect, useRef, useState, useMemo } from 'react';
import { geoOrthographic, geoPath, geoGraticule } from 'd3-geo';
import { feature } from 'topojson-client';

const LD_INK    = '#0F2A4A';
const LD_FACE   = '#EFE9DD';
const LD_MUTED  = '#5B6878';
const LD_TEAL   = '#0E7C8B';
const LD_ACCENT = '#3A7BD5';

const STAGES = [
  { id: 'forensics', label: 'PDF Forensics',    desc: 'OCR + document type detection',       ms: 1600 },
  { id: 'extract',  label: 'Text Extraction',   desc: 'pdfplumber + Tesseract Romanian pack', ms: 2000 },
  { id: 'classify', label: 'Classification',    desc: 'DOC_HDR / DOC_BIS · zone anchoring',  ms: 2200 },
  { id: 'fields',   label: 'Structured Fields', desc: 'Demographics, labs, checkboxes',       ms: 2800 },
  { id: 'llm',      label: 'LLM Epicriza',      desc: 'Claude AI clinical narrative parsing', ms: 7000 },
  { id: 'fhir',     label: 'FHIR R4 Assembly',  desc: 'Patient, Encounter, Conditions…',      ms: 4500 },
  { id: 'validate', label: 'Validate & Sign',   desc: 'Conformance check · provenance hash',  ms: 3000 },
];

const STAGE_TARGETS = [
  { res: 0,  codes: 0,  refs: 0  },
  { res: 4,  codes: 5,  refs: 2  },
  { res: 10, codes: 10, refs: 7  },
  { res: 16, codes: 13, refs: 11 },
  { res: 20, codes: 15, refs: 14 },
  { res: 24, codes: 17, refs: 17 },
  { res: 24, codes: 17, refs: 18 },
];

const TIDBITS = [
  'FHIR encodes care as small resources — Patient, Encounter, Observation, Condition, Procedure — tied together by a Bundle.',
  'Every coded value links to a code system: ICD-10 for diagnoses, LOINC for labs, RxNorm for medications, SNOMED CT for the rest.',
  'US Core 6.1.0 tightens FHIR for the US healthcare context, defining the must-support fields each resource needs.',
  'A bundle ships with a signed manifest — validation must pass before it\'s accepted by downstream systems.',
  'A typical discharge document maps to 20–30 FHIR resources across 6–8 distinct types.',
];

// ── Spinning globe with real country outlines ─────────────────────
function Globe({ size = 360 }: { size?: number }) {
  const [land, setLand] = useState<any>(null);
  const landRef = useRef<SVGPathElement>(null);
  const gratRef = useRef<SVGPathElement>(null);

  useEffect(() => {
    let cancelled = false;
    fetch('https://unpkg.com/world-atlas@2.0.2/countries-110m.json')
      .then(r => r.json())
      .then((world: any) => {
        if (cancelled) return;
        setLand((feature as any)(world, world.objects.countries));
      })
      .catch(err => console.error('world-atlas load failed', err));
    return () => { cancelled = true; };
  }, []);

  useEffect(() => {
    if (!land) return;
    const c = size / 2;
    const projection = geoOrthographic().scale(size * 0.36).translate([c, c]).clipAngle(90);
    const pathGen = geoPath(projection);
    const graticule = geoGraticule().step([20, 20])();
    let raf: number;
    let last = performance.now();
    let lon = 0;
    const tick = (now: number) => {
      const dt = now - last; last = now;
      lon += dt * 0.022;
      projection.rotate([lon, -22, 0]);
      if (landRef.current) landRef.current.setAttribute('d', pathGen(land as any) ?? '');
      if (gratRef.current) gratRef.current.setAttribute('d', pathGen(graticule) ?? '');
      raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [land, size]);

  const c = size / 2;
  const r = size * 0.36;
  return (
    <g>
      <defs>
        <radialGradient id="ldTerm" cx="38%" cy="36%" r="68%">
          <stop offset="0%"   stopColor="#FFFFFF" stopOpacity="0.22" />
          <stop offset="55%"  stopColor="#FFFFFF" stopOpacity="0" />
          <stop offset="100%" stopColor="#000000" stopOpacity="0.22" />
        </radialGradient>
        <clipPath id="ldSphereClip"><circle cx={c} cy={c} r={r} /></clipPath>
      </defs>
      <circle cx={c} cy={c} r={r} fill={LD_FACE} stroke={LD_INK} strokeWidth="1" />
      <path ref={gratRef} fill="none" stroke={LD_INK} strokeWidth="0.4" opacity={0.18} />
      <path ref={landRef} fill={LD_INK} stroke="none" />
      <circle cx={c} cy={c} r={r} fill="url(#ldTerm)" clipPath="url(#ldSphereClip)" style={{ pointerEvents: 'none' }} />
    </g>
  );
}

// ── Concentric whirl rings + comet streaks + micro-particles ──────
function Whirl({ size = 360 }: { size?: number }) {
  const c = size / 2;
  return (
    <g>
      <g className="ld-whirl-slow">
        <circle cx={c} cy={c} r={c * 0.96} fill="none" stroke={LD_INK} strokeWidth="0.5" strokeDasharray="0.6 6" opacity={0.5} />
      </g>
      <g className="ld-whirl-ccw">
        <circle cx={c} cy={c} r={c * 0.88} fill="none" stroke={LD_INK} strokeWidth="0.6" strokeDasharray="3 14" opacity={0.3} />
      </g>
      <g className="ld-whirl-cw">
        <circle cx={c} cy={c} r={c * 0.81} fill="none" stroke={LD_INK} strokeWidth="0.5" strokeDasharray="1.2 5" opacity={0.45} />
      </g>
      <g className="ld-streak-cw">
        <path
          d={`M ${c} ${c - c * 0.89} A ${c * 0.89} ${c * 0.89} 0 0 1 ${c + c * 0.65} ${c - c * 0.6}`}
          fill="none" stroke={LD_ACCENT} strokeWidth="1.6" strokeLinecap="round" opacity={0.85}
        />
        <circle cx={c + c * 0.65} cy={c - c * 0.6} r="2.6" fill={LD_ACCENT} />
      </g>
      <g className="ld-streak-cw" style={{ animationDelay: '-1.8s', opacity: 0.55 }}>
        <path
          d={`M ${c} ${c - c * 0.89} A ${c * 0.89} ${c * 0.89} 0 0 1 ${c + c * 0.41} ${c - c * 0.76}`}
          fill="none" stroke={LD_INK} strokeWidth="1.2" strokeLinecap="round" opacity={0.5}
        />
      </g>
      <g className="ld-streak-ccw">
        <path
          d={`M ${c - c * 0.65} ${c + c * 0.47} A ${c * 0.89} ${c * 0.89} 0 0 1 ${c - c * 0.87} ${c - c * 0.06}`}
          fill="none" stroke={LD_TEAL} strokeWidth="1.2" strokeLinecap="round" opacity={0.65}
        />
        <circle cx={c - c * 0.87} cy={c - c * 0.06} r="1.8" fill={LD_TEAL} opacity={0.9} />
      </g>
      <g className="ld-micro-cw">
        <circle cx={c}            cy={c - c * 0.87} r="1"   fill={LD_INK} opacity={0.8} />
        <circle cx={c + c * 0.87} cy={c}            r="0.8" fill={LD_INK} opacity={0.55} />
        <circle cx={c}            cy={c + c * 0.87} r="1.1" fill={LD_INK} opacity={0.7} />
        <circle cx={c - c * 0.87} cy={c}            r="0.7" fill={LD_INK} opacity={0.5} />
      </g>
    </g>
  );
}

// ── Smooth tweening counter ───────────────────────────────────────
function LDCount({ target }: { target: number }) {
  const [v, setV] = useState(0);
  const fromRef = useRef(0);
  useEffect(() => {
    const from = fromRef.current;
    const start = performance.now();
    const ms = 800;
    let raf: number;
    const tick = (now: number) => {
      const t = Math.min(1, (now - start) / ms);
      const e = 1 - Math.pow(1 - t, 3);
      setV(Math.round(from + (target - from) * e));
      if (t < 1) raf = requestAnimationFrame(tick);
      else fromRef.current = target;
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [target]);
  return <>{v}</>;
}

// ── Main LoadingScreen ────────────────────────────────────────────
interface LoadingScreenProps {
  fileName?: string;
}

export function LoadingScreen({ fileName }: LoadingScreenProps) {
  const [active, setActive]     = useState(0);
  const [done, setDone]         = useState<number[]>([]);
  const [counters, setCounters] = useState(STAGE_TARGETS[0]);
  const [tidbitIdx, setTidbitIdx] = useState(0);

  useEffect(() => {
    let cancel = false;
    let i = 0;
    const tick = () => {
      if (cancel || i >= STAGES.length) return;
      setActive(i);
      setCounters(STAGE_TARGETS[i]);
      const ms = Math.min(STAGES[i].ms, 1300);
      setTimeout(() => {
        if (cancel) return;
        setDone(d => [...d, i]);
        i++;
        tick();
      }, ms);
    };
    tick();
    return () => { cancel = true; };
  }, []);

  useEffect(() => {
    const t = setInterval(() => setTidbitIdx(i => (i + 1) % TIDBITS.length), 4000);
    return () => clearInterval(t);
  }, []);

  const progress = done.length / STAGES.length;
  const ARC_R = 230;
  const ARC_C = 2 * Math.PI * ARC_R;

  const motes = useMemo(() => Array.from({ length: 16 }, (_, i) => {
    const angle = (i / 16) * 360 + (Math.random() * 16 - 8);
    const dist  = 200 + Math.random() * 110;
    return {
      dx: Math.cos(angle * Math.PI / 180) * dist,
      dy: Math.sin(angle * Math.PI / 180) * dist,
      duration: 3.5 + Math.random() * 4,
      delay: -Math.random() * 6,
      size: 1 + Math.random() * 2,
    };
  }), []);

  const displayName = fileName ?? 'discharge-summary.pdf';
  const eta = Math.max(1, Math.round(6 - progress * 6));

  return (
    <div style={{
      flex: 1, position: 'relative', overflow: 'hidden',
      background: 'radial-gradient(ellipse at 50% 38%, #FAF6EE 0%, #F2EBDC 70%, #ECE2CB 100%)',
      color: LD_INK,
    }}>
      {/* Breathing glow */}
      <div aria-hidden style={{
        position: 'absolute', top: '50%', left: '50%',
        width: 760, height: 760, transform: 'translate(-50%, -50%)',
        background: 'radial-gradient(circle, rgba(58,123,213,.08) 0%, transparent 60%)',
        animation: 'ld-breath 5.5s ease-in-out infinite',
        pointerEvents: 'none',
      }} />
      {/* Film grain */}
      <div aria-hidden style={{
        position: 'absolute', inset: 0, pointerEvents: 'none',
        backgroundImage: 'radial-gradient(rgba(15,42,74,.04) 1px, transparent 1px)',
        backgroundSize: '3px 3px', mixBlendMode: 'multiply',
      }} />

      {/* File info — top-left */}
      <div style={{ position: 'absolute', top: 28, left: 36, zIndex: 5 }}>
        <div style={{ fontSize: 11, letterSpacing: 1.8, color: LD_MUTED, textTransform: 'uppercase', fontWeight: 600 }}>Processing</div>
        <div style={{ marginTop: 6, fontFamily: '"IBM Plex Mono", monospace', fontSize: 12.5, color: LD_INK }}>{displayName}</div>
        <div style={{ fontFamily: '"IBM Plex Mono", monospace', fontSize: 11, color: LD_MUTED, marginTop: 2 }}>EHDS Pipeline · stage {Math.min(active + 1, STAGES.length)} of {STAGES.length}</div>
      </div>

      {/* Progress % — top-right */}
      <div style={{ position: 'absolute', top: 28, right: 36, textAlign: 'right', zIndex: 5 }}>
        <div style={{ fontSize: 11, letterSpacing: 1.8, color: LD_MUTED, textTransform: 'uppercase', fontWeight: 600 }}>Progress</div>
        <div style={{ marginTop: 4, fontFamily: '"IBM Plex Mono", monospace', fontSize: 22, fontWeight: 500, color: LD_INK, letterSpacing: -0.4 }}>{Math.round(progress * 100)}%</div>
        <div style={{ fontFamily: '"IBM Plex Mono", monospace', fontSize: 11, color: LD_MUTED, marginTop: 2 }}>~{eta}s remaining</div>
      </div>

      {/* Center column: globe → caption → counters */}
      <div style={{
        position: 'absolute', inset: 0,
        display: 'flex', flexDirection: 'column',
        alignItems: 'center', justifyContent: 'center',
        gap: 28, padding: '108px 260px 88px 60px',
        pointerEvents: 'none',
      }}>
        {/* Globe stage */}
        <div style={{ position: 'relative', width: 460, height: 460, flexShrink: 0 }}>
          {motes.map((m, i) => (
            <div key={i} className="ld-mote" style={{
              position: 'absolute', top: '50%', left: '50%',
              width: m.size, height: m.size, borderRadius: m.size,
              background: LD_INK,
              marginLeft: -m.size / 2, marginTop: -m.size / 2,
              '--ld-x': `${m.dx}px`,
              '--ld-y': `${m.dy}px`,
              animationDuration: `${m.duration}s`,
              animationDelay: `${m.delay}s`,
            } as React.CSSProperties} />
          ))}

          <svg width="460" height="460" viewBox="0 0 500 500" style={{ position: 'relative', zIndex: 1, display: 'block' }}>
            {/* Embracing progress arc */}
            <circle cx="250" cy="250" r={ARC_R} fill="none" stroke={LD_INK} strokeWidth="0.5" opacity="0.1" />
            <circle cx="250" cy="250" r={ARC_R} fill="none" stroke={LD_ACCENT} strokeWidth="1.6"
              strokeLinecap="round"
              strokeDasharray={ARC_C}
              strokeDashoffset={ARC_C * (1 - progress)}
              transform="rotate(-90 250 250)"
              style={{ transition: 'stroke-dashoffset .9s cubic-bezier(.2,.7,.3,1)' }}
            />
            <g transform="translate(70 70)">
              <Whirl size={360} />
              <Globe size={360} />
            </g>
          </svg>
        </div>

        {/* Stage caption */}
        <div style={{ textAlign: 'center', minHeight: 76 }}>
          <div key={active} style={{ animation: 'ld-fade-in .6s ease both' }}>
            <div style={{ fontSize: 11, letterSpacing: 2, color: LD_MUTED, textTransform: 'uppercase', fontWeight: 600 }}>
              Stage {Math.min(active + 1, STAGES.length)} of {STAGES.length}
            </div>
            <div style={{ marginTop: 8, fontSize: 22, fontWeight: 500, color: LD_INK, letterSpacing: -0.5 }}>
              {STAGES[Math.min(active, STAGES.length - 1)].label}
            </div>
            <div style={{ marginTop: 4, fontSize: 13, color: LD_MUTED, fontFamily: '"IBM Plex Mono", monospace' }}>
              {STAGES[Math.min(active, STAGES.length - 1)].desc}
            </div>
          </div>
        </div>

        {/* Live counters */}
        <div style={{ display: 'flex', gap: 72 }}>
          {([
            { k: 'Resources mapped', v: counters.res  },
            { k: 'Codes resolved',   v: counters.codes },
            { k: 'References built', v: counters.refs  },
          ] as const).map(c => (
            <div key={c.k} style={{ textAlign: 'center', minWidth: 110 }}>
              <div style={{ fontSize: 28, fontWeight: 500, color: LD_INK, fontFamily: '"IBM Plex Mono", monospace', letterSpacing: -0.5, fontFeatureSettings: '"tnum"' }}>
                <LDCount target={c.v} />
              </div>
              <div style={{ marginTop: 2, fontSize: 11, color: LD_MUTED, letterSpacing: 1.4, textTransform: 'uppercase', fontWeight: 600 }}>{c.k}</div>
            </div>
          ))}
        </div>
      </div>

      {/* Pipeline — absolute right */}
      <div style={{ position: 'absolute', top: '50%', right: 60, transform: 'translateY(-50%)', zIndex: 4, display: 'flex', flexDirection: 'column', gap: 2 }}>
        {STAGES.map((s, i) => {
          const isDone   = done.includes(i);
          const isActive = active === i && !isDone;
          return (
            <div key={s.id} style={{
              display: 'flex', alignItems: 'center', gap: 12, padding: '8px 0',
              opacity: isDone || isActive ? 1 : 0.4, transition: 'opacity .35s',
            }}>
              <div style={{
                width: 18, height: 18, borderRadius: 9, flexShrink: 0,
                background: isDone ? LD_INK : 'transparent',
                border: `1.5px solid ${LD_INK}`,
                boxShadow: isActive ? '0 0 0 5px rgba(15,42,74,.1)' : 'none',
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                transition: 'all .3s',
              }}>
                {isDone && (
                  <svg width="9" height="9" viewBox="0 0 9 9" fill="none" stroke="#FAF6EE" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M2 4.5L4 6.5L7.5 3" />
                  </svg>
                )}
                {isActive && (
                  <div style={{ width: 6, height: 6, borderRadius: 3, background: LD_INK, animation: 'ld-pulse 1.1s ease-in-out infinite' }} />
                )}
              </div>
              <div style={{ minWidth: 134 }}>
                <div style={{ fontSize: 12.5, fontWeight: 500, color: LD_INK }}>{s.label}</div>
                <div style={{ fontSize: 10.5, color: LD_MUTED, marginTop: 1, fontFamily: '"IBM Plex Mono", monospace' }}>{s.desc}</div>
              </div>
            </div>
          );
        })}
      </div>

      {/* Rotating tidbit */}
      <div style={{ position: 'absolute', bottom: 22, left: 0, right: 0, textAlign: 'center', padding: '0 60px' }}>
        <div key={tidbitIdx} style={{ fontSize: 12, color: LD_MUTED, fontStyle: 'italic', maxWidth: 720, margin: '0 auto', lineHeight: 1.5, animation: 'ld-fade-in 1s ease both' }}>
          {TIDBITS[tidbitIdx]}
        </div>
      </div>
    </div>
  );
}

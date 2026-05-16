import { useEffect, useState } from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import type { Role } from '../App';

const BLUE   = '#0F2A4A';
const ACCENT = '#3A7BD5';
const BORDER = '#E5E9F0';
const TEXT   = '#1A2433';
const MUTED  = '#5B6878';
const WARN   = '#C03A2B';

// ─── Helpers ────────────────────────────────────────────────────

function resources(bundle: any, type: string): any[] {
  return (bundle?.entry ?? []).map((e: any) => e.resource).filter((r: any) => r?.resourceType === type);
}

function bestDisplay(cc: any): string {
  if (!cc) return '—';
  if (cc.text) return cc.text;
  return cc.coding?.[0]?.display || cc.coding?.[0]?.code || '—';
}

function getCode(cc: any, systemFragment: string): string | null {
  return cc?.coding?.find((c: any) => c.system?.toLowerCase().includes(systemFragment))?.code ?? null;
}

function patientName(p: any): string {
  if (!p?.name?.length) return '—';
  const n = p.name[0];
  return [[...(n.given ?? [])].join(' '), n.family].filter(Boolean).join(' ') || n.text || '—';
}

function fmtDate(s?: string): string {
  if (!s) return '—';
  try { return new Date(s).toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: 'numeric' }); }
  catch { return s; }
}

function fmtDateTime(s?: string): string {
  if (!s) return '—';
  try { return new Date(s).toLocaleString('en-GB', { day: '2-digit', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit' }); }
  catch { return s; }
}

function calcAge(birthDate?: string): string {
  if (!birthDate) return '';
  try {
    const birth = new Date(birthDate);
    const today = new Date();
    let age = today.getFullYear() - birth.getFullYear();
    const m = today.getMonth() - birth.getMonth();
    if (m < 0 || (m === 0 && today.getDate() < birth.getDate())) age--;
    return `age ${age}`;
  } catch { return ''; }
}

function encounterPeriod(enc: any): { start?: string; end?: string } {
  const p = enc?.actualPeriod ?? enc?.period;
  return { start: p?.start, end: p?.end };
}

function encounterDuration(enc: any): string {
  const { start: s, end: e } = encounterPeriod(enc);
  if (!s || !e) return '—';
  const hrs = (new Date(e).getTime() - new Date(s).getTime()) / 3_600_000;
  if (hrs < 24) return `${Math.round(hrs)}h (day-hospital)`;
  const days = Math.round(hrs / 24);
  return `${days} day${days !== 1 ? 's' : ''}`;
}

function capitalize(s: string): string {
  return s.charAt(0).toUpperCase() + s.slice(1).toLowerCase();
}

function shortSystem(system?: string): string {
  if (!system) return 'ID';
  if (system.includes('cnp') || system.includes('ro:')) return 'CNP';
  if (system.includes('oid')) return 'OID';
  const parts = system.split(/[/:]/);
  return (parts[parts.length - 1] || 'ID').toUpperCase().slice(0, 8);
}

// ─── Animated counter ────────────────────────────────────────────

function useCount(target: number, ms = 800) {
  const [v, setV] = useState(0);
  useEffect(() => {
    const start = performance.now();
    let raf: number;
    const tick = (now: number) => {
      const t = Math.min(1, (now - start) / ms);
      const e = 1 - Math.pow(1 - t, 3);
      setV(Math.round(target * e));
      if (t < 1) raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [target, ms]);
  return v;
}

// ─── Section animation wrapper ───────────────────────────────────

function Section({ id, show, children }: { id: string; show: boolean; children: React.ReactNode }) {
  return (
    <AnimatePresence initial={false}>
      {show && (
        <motion.div
          key={id}
          initial={{ opacity: 0, height: 0 }}
          animate={{ opacity: 1, height: 'auto', transition: { duration: 0.32, ease: 'easeOut' } }}
          exit={{ opacity: 0, height: 0, transition: { duration: 0.28, ease: 'easeIn' } }}
          style={{ overflow: 'hidden' }}
        >
          <div style={{ paddingBottom: 16 }}>{children}</div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}

// ─── Redacted value placeholder ──────────────────────────────────

function Redacted({ width }: { width?: number }) {
  return (
    <span style={{
      display: 'inline-flex', alignItems: 'center',
      width: width ?? 'auto',
      fontSize: 11, fontFamily: '"IBM Plex Mono", monospace',
      background: '#EEF2F7', color: '#9AA8BA',
      padding: '3px 9px', borderRadius: 4,
      border: '1px dashed #C8D4E0',
      letterSpacing: 2,
      userSelect: 'none',
      gap: 5,
    }}>
      <svg width="9" height="11" viewBox="0 0 9 11" fill="none" style={{ flexShrink: 0 }}>
        <rect x="1" y="4.5" width="7" height="6" rx="1" stroke="#9AA8BA" strokeWidth="1.2"/>
        <path d="M2.5 4.5V3a2 2 0 0 1 4 0v1.5" stroke="#9AA8BA" strokeWidth="1.2" strokeLinecap="round"/>
      </svg>
      RESTRICTED
    </span>
  );
}

// ─── Sub-components ──────────────────────────────────────────────

function StatCard({ label, value, sub, accent }: { label: string; value: number; sub?: string; accent?: string }) {
  const n = useCount(value);
  return (
    <div style={{ background: '#fff', border: `1px solid ${BORDER}`, borderRadius: 8, padding: '14px 16px' }}>
      <div style={{ fontSize: 11, letterSpacing: 1.2, color: MUTED, textTransform: 'uppercase', fontWeight: 600 }}>{label}</div>
      <div style={{ marginTop: 6, fontSize: 26, fontWeight: 600, color: accent || BLUE, letterSpacing: -0.5, fontFeatureSettings: '"tnum"' }}>{n}</div>
      {sub && <div style={{ fontSize: 11, color: MUTED, marginTop: 2 }}>{sub}</div>}
    </div>
  );
}

function ClinicalCard({ title, badge, badgeColor, icon, children }: {
  title: string; badge?: number; badgeColor?: string; icon?: string; children: React.ReactNode;
}) {
  return (
    <div style={{ background: '#fff', border: `1px solid ${BORDER}`, borderRadius: 10, padding: '16px 18px' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 10, paddingBottom: 10, borderBottom: `1px solid ${BORDER}` }}>
        {icon && (
          <div style={{
            width: 22, height: 22, borderRadius: 4, background: BLUE, color: '#fff',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            fontSize: 10, fontWeight: 700, fontFamily: '"IBM Plex Mono", monospace', flexShrink: 0,
          }}>{icon}</div>
        )}
        <div style={{ fontSize: 14, fontWeight: 600, color: TEXT, flex: 1, letterSpacing: -0.1 }}>{title}</div>
        {badge != null && (
          <span style={{
            fontSize: 11, fontWeight: 600, fontFamily: '"IBM Plex Mono", monospace',
            background: (badgeColor || BLUE) + '18', color: badgeColor || BLUE,
            padding: '2px 8px', borderRadius: 10,
          }}>{badge}</span>
        )}
      </div>
      {children}
    </div>
  );
}

function Field({ k, v, big, mono, children }: { k: string; v?: string; big?: boolean; mono?: boolean; children?: React.ReactNode }) {
  return (
    <div>
      <div style={{ fontSize: 10, color: MUTED, letterSpacing: 0.5, textTransform: 'uppercase', fontWeight: 500, marginBottom: 3 }}>{k}</div>
      <div style={{ fontSize: big ? 15 : 13, fontWeight: big ? 600 : 500, color: TEXT, fontFamily: mono ? '"IBM Plex Mono", monospace' : 'inherit' }}>
        {children ?? (v || '—')}
      </div>
    </div>
  );
}

function IcdBadge({ code }: { code: string }) {
  return (
    <span style={{
      fontFamily: '"IBM Plex Mono", monospace', fontSize: 11,
      background: '#F0F4F9', color: BLUE, padding: '2px 6px', borderRadius: 4, fontWeight: 500,
    }}>{code}</span>
  );
}

function CodeBadge({ label, value, color }: { label: string; value: string; color: 'blue' | 'amber' | 'teal' }) {
  const styles: Record<string, { color: string; bg: string; border: string }> = {
    blue:  { color: ACCENT,   bg: '#EEF4FC', border: '#C9D8F0' },
    amber: { color: '#A86A00', bg: '#FFF8E8', border: '#F0DFA0' },
    teal:  { color: '#0D6E5A', bg: '#EDF7F4', border: '#B8DDD4' },
  };
  const s = styles[color];
  return (
    <span style={{
      display: 'inline-flex', alignItems: 'center', gap: 4,
      fontSize: 10, fontFamily: '"IBM Plex Mono", monospace',
      border: `1px solid ${s.border}`, borderRadius: 4,
      padding: '2px 7px', color: s.color, background: s.bg,
    }}>
      <span style={{ opacity: 0.6 }}>{label}</span>
      {value}
    </span>
  );
}

// ─── Lab aggregate view for Statistician ─────────────────────────

function LabAggregate({ obs }: { obs: any[] }) {
  const highCount   = obs.filter((o: any) => o.interpretation?.[0]?.coding?.[0]?.code === 'H').length;
  const lowCount    = obs.filter((o: any) => o.interpretation?.[0]?.coding?.[0]?.code === 'L').length;
  const abnCount    = obs.filter((o: any) => o.interpretation?.[0]?.coding?.[0]?.code === 'A').length;
  const normalCount = obs.length - highCount - lowCount - abnCount;
  const bars = [
    { label: 'Normal', count: normalCount, color: '#0E8559', bg: '#EDF7F4' },
    { label: 'High (H)', count: highCount,   color: WARN,      bg: '#FCEDEB' },
    { label: 'Low (L)',  count: lowCount,    color: '#A86A00', bg: '#FFF8E8' },
    { label: 'Abnormal (A)', count: abnCount, color: '#6D4ED8', bg: '#F3EFFC' },
  ];
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
      <div style={{ fontSize: 12, color: MUTED, marginBottom: 2 }}>
        Aggregate distribution — {obs.length} results total · individual values not accessible at this access level
      </div>
      {bars.filter(b => b.count > 0 || b.label === 'Normal').map(b => {
        const pct = obs.length > 0 ? Math.round((b.count / obs.length) * 100) : 0;
        return (
          <div key={b.label}>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12, marginBottom: 4 }}>
              <span style={{ color: TEXT, fontWeight: 500 }}>{b.label}</span>
              <span style={{ fontFamily: '"IBM Plex Mono", monospace', color: b.color, fontWeight: 600 }}>{b.count}</span>
            </div>
            <div style={{ height: 6, borderRadius: 3, background: '#EEF2F7', overflow: 'hidden' }}>
              <motion.div
                initial={{ width: 0 }}
                animate={{ width: `${pct}%` }}
                transition={{ duration: 0.7, ease: 'easeOut' }}
                style={{ height: '100%', background: b.color, borderRadius: 3 }}
              />
            </div>
          </div>
        );
      })}
    </div>
  );
}

// ─── Main panel ──────────────────────────────────────────────────

export function FHIRSummaryPanel({ bundle, role = 'doctor' }: { bundle: any; role?: Role }) {
  const patients     = resources(bundle, 'Patient');
  const encounters   = resources(bundle, 'Encounter');
  const conditions   = resources(bundle, 'Condition');
  const meds         = resources(bundle, 'MedicationRequest');
  const obs          = resources(bundle, 'Observation');
  const procedures   = resources(bundle, 'Procedure');
  const adverse      = resources(bundle, 'AdverseEvent');
  const compositions = resources(bundle, 'Composition');
  const allergies    = resources(bundle, 'AllergyIntolerance');

  const patient   = patients[0];
  const encounter = encounters[0];
  const comp      = compositions[0];

  const loincCode  = comp?.type?.coding?.[0]?.code;
  const docLabel   = loincCode === '34105-7' ? 'Hospital Discharge (DOC_HDR)'
    : loincCode === '34133-9' ? 'Day-Hospital / Ambulatory (DOC_BIS)'
    : loincCode ?? '—';

  const encPeriod = encounterPeriod(encounter);
  const totalResources = bundle?.entry?.length ?? 0;
  const abnormalObs = obs.filter((o: any) => {
    const code = o.interpretation?.[0]?.coding?.[0]?.code ?? '';
    return code === 'A' || code === 'H' || code === 'L';
  });

  // ── Access flags ──────────────────────────────────────────────
  const showPatientPII      = role === 'doctor';
  const showEncounterDates  = role === 'doctor';
  const showPatientCard     = role !== 'statistician';
  const showEncounterCard   = role !== 'statistician';
  const showMedications     = role === 'doctor';
  const showProcedures      = role === 'doctor';
  const showAllergies       = role === 'doctor';
  const showAdverseEvents   = role === 'doctor';
  const showLabIndividual   = role !== 'statistician';
  const showDiagnosisText   = role !== 'statistician';
  const showDiagnosisSnomed = role === 'doctor';

  return (
    <div style={{ display: 'flex', flexDirection: 'column' }}>

      {/* Stats row — always visible */}
      <div style={{ paddingBottom: 16 }}>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5, 1fr)', gap: 12 }}>
          <StatCard label="FHIR resources" value={totalResources} sub="across resource types" />
          <StatCard label="Diagnoses" value={conditions.length} sub="ICD-10 coded" />
          <StatCard label="Abnormal labs" value={abnormalObs.length} sub="flagged H/L/A" accent={abnormalObs.length > 0 ? WARN : undefined} />
          <StatCard label="Medications" value={meds.length} sub="active orders" />
          <StatCard label="Procedures" value={procedures.length} sub="documented" />
        </div>
      </div>

      {/* Patient + Encounter — hidden for Statistician */}
      <Section id="patient-encounter" show={showPatientCard || showEncounterCard}>
        <div style={{ display: 'grid', gridTemplateColumns: '1.1fr 1fr', gap: 16 }}>
          {showPatientCard && (
            <ClinicalCard title="Patient" icon="P">
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '14px 24px' }}>
                <Field k="Full name" big>
                  {showPatientPII ? patientName(patient) : <Redacted />}
                </Field>
                <Field k="Date of birth">
                  {showPatientPII
                    ? (patient?.birthDate ? `${fmtDate(patient.birthDate)} (${calcAge(patient.birthDate)})` : '—')
                    : <Redacted />}
                </Field>
                <Field k="Gender" v={patient?.gender ? capitalize(patient.gender) : undefined} />
                <Field k="Blood group" v={patient?.extension?.find((x: any) => x.url?.includes('blood'))?.valueString} />
                {(patient?.identifier ?? []).slice(0, 2).map((id: any, i: number) => (
                  <Field key={i} k={shortSystem(id.system)} mono>
                    {showPatientPII ? id.value : <Redacted />}
                  </Field>
                ))}
              </div>
            </ClinicalCard>
          )}

          {showEncounterCard && (
            <ClinicalCard title="Encounter" icon="E">
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '14px 24px' }}>
                <Field k="Admitted">
                  {showEncounterDates ? fmtDateTime(encPeriod.start) : <Redacted />}
                </Field>
                <Field k="Discharged">
                  {showEncounterDates ? fmtDateTime(encPeriod.end) : <Redacted />}
                </Field>
                <Field k="Length of stay" v={encounterDuration(encounter)} big />
                <Field k="Document type" v={docLabel} />
              </div>
            </ClinicalCard>
          )}
        </div>
      </Section>

      {/* Diagnoses — always visible, detail level varies */}
      {conditions.length > 0 && (
        <div style={{ paddingBottom: 16 }}>
          <ClinicalCard title="Diagnoses" badge={conditions.length}>
            <div style={{ display: 'flex', flexDirection: 'column' }}>
              {conditions.map((cond: any, i: number) => {
                const display = bestDisplay(cond.code);
                const snomed  = getCode(cond.code, 'snomed');
                const icd10   = getCode(cond.code, 'icd-10') ?? getCode(cond.code, 'icd10');
                const icdChapter = icd10 ? icd10.slice(0, 3) : null;
                const isPrimary = i === 0;
                return (
                  <div key={i} style={{ padding: '10px 0', borderBottom: `1px solid ${BORDER}`, display: 'flex', alignItems: 'flex-start', gap: 10 }}>
                    {/* Statistician sees chapter-level ICD only */}
                    {role === 'statistician'
                      ? (icdChapter && <IcdBadge code={icdChapter} />)
                      : (icd10 && <IcdBadge code={icd10} />)}
                    <div style={{ flex: 1 }}>
                      {showDiagnosisText && (
                        <span style={{ fontSize: 13.5, color: TEXT }}>{display}</span>
                      )}
                      {!showDiagnosisText && (
                        <span style={{ fontSize: 12, color: MUTED, fontStyle: 'italic' }}>
                          {icdChapter ? `ICD-10 chapter ${icdChapter}` : '—'}
                        </span>
                      )}
                      {showDiagnosisSnomed && snomed && (
                        <div style={{ marginTop: 4 }}>
                          <CodeBadge label="SNOMED" value={snomed} color="teal" />
                        </div>
                      )}
                    </div>
                    {isPrimary && showDiagnosisText && (
                      <span style={{ fontSize: 10, fontWeight: 600, color: BLUE, letterSpacing: 1, textTransform: 'uppercase', flexShrink: 0 }}>Primary</span>
                    )}
                  </div>
                );
              })}
            </div>
          </ClinicalCard>
        </div>
      )}

      {/* Medications — Doctor only */}
      <Section id="medications" show={showMedications && meds.length > 0}>
        <ClinicalCard title="Medications" badge={meds.length}>
          <div style={{ display: 'flex', flexDirection: 'column' }}>
            {meds.map((med: any, i: number) => {
              const name   = bestDisplay(med.medicationCodeableConcept);
              const atc    = getCode(med.medicationCodeableConcept, 'atc') ?? getCode(med.medicationCodeableConcept, 'whocc');
              const dosage = med.dosageInstruction?.[0]?.text;
              return (
                <div key={i} style={{ padding: '8px 0', borderBottom: `1px solid ${BORDER}`, display: 'flex', alignItems: 'baseline', gap: 8, fontSize: 13 }}>
                  <span style={{ flex: 1, fontWeight: 500, color: TEXT }}>{name}</span>
                  {dosage && <span style={{ fontSize: 11, color: MUTED, flexShrink: 0 }}>{dosage}</span>}
                  {atc && <CodeBadge label="ATC" value={atc} color="teal" />}
                </div>
              );
            })}
          </div>
        </ClinicalCard>
      </Section>

      {/* Lab Results — all roles, but detail level varies */}
      {obs.length > 0 && (
        <div style={{ paddingBottom: 16 }}>
          <ClinicalCard
            title={`Lab Results${abnormalObs.length ? ` — ${abnormalObs.length} abnormal` : ''}`}
            badge={obs.length}
            badgeColor={abnormalObs.length > 0 ? WARN : undefined}
          >
            {showLabIndividual ? (
              <div className="custom-scrollbar" style={{ maxHeight: 260, overflowY: 'auto' }}>
                {obs.slice(0, 20).map((o: any, i: number) => {
                  const name     = bestDisplay(o.code);
                  const val      = o.valueQuantity?.value;
                  const unit     = o.valueQuantity?.unit ?? '';
                  const loinc    = getCode(o.code, 'loinc');
                  const flag     = o.interpretation?.[0]?.coding?.[0]?.code ?? '';
                  const isAbnorm = flag === 'A' || flag === 'H' || flag === 'L';
                  return (
                    <div key={i} style={{
                      padding: '8px 0', borderBottom: `1px solid ${BORDER}`,
                      display: 'grid', gridTemplateColumns: '1.3fr 1fr auto',
                      gap: 8, alignItems: 'baseline',
                    }}>
                      <div>
                        <div style={{ fontSize: 13, fontWeight: 500, color: isAbnorm ? WARN : TEXT }}>{name}</div>
                        {loinc && <div style={{ fontSize: 10, color: MUTED, fontFamily: '"IBM Plex Mono", monospace', marginTop: 1 }}>{loinc}</div>}
                      </div>
                      {val !== undefined && (
                        <div style={{ fontFamily: '"IBM Plex Mono", monospace', fontSize: 13, color: TEXT }}>
                          <span style={{ fontWeight: 600 }}>{val}</span>{' '}
                          <span style={{ fontSize: 10, color: MUTED }}>{unit}</span>
                        </div>
                      )}
                      {isAbnorm && (
                        <span style={{
                          fontFamily: '"IBM Plex Mono", monospace', fontSize: 10, fontWeight: 600,
                          background: flag === 'H' || flag === 'A' ? '#FCEDEB' : '#FFF4E0',
                          color: flag === 'H' || flag === 'A' ? WARN : '#A86A00',
                          padding: '2px 6px', borderRadius: 4,
                        }}>{flag}</span>
                      )}
                    </div>
                  );
                })}
                {obs.length > 20 && (
                  <p style={{ textAlign: 'center', fontSize: 12, color: MUTED, marginTop: 8 }}>+{obs.length - 20} more</p>
                )}
              </div>
            ) : (
              <LabAggregate obs={obs} />
            )}
          </ClinicalCard>
        </div>
      )}

      {/* Procedures — Doctor only */}
      <Section id="procedures" show={showProcedures && procedures.length > 0}>
        <ClinicalCard title="Procedures" badge={procedures.length}>
          <div style={{ display: 'flex', flexDirection: 'column' }}>
            {procedures.map((proc: any, i: number) => {
              const name = bestDisplay(proc.code);
              const date = proc.performedDateTime ?? proc.performedPeriod?.start;
              const cpt  = getCode(proc.code, 'cpt');
              return (
                <div key={i} style={{ padding: '8px 0', borderBottom: `1px solid ${BORDER}`, display: 'flex', alignItems: 'center', gap: 10, fontSize: 13 }}>
                  {cpt && <IcdBadge code={cpt} />}
                  <span style={{ flex: 1, color: TEXT }}>{name}</span>
                  {date && <span style={{ fontSize: 11, color: MUTED, fontFamily: '"IBM Plex Mono", monospace' }}>{fmtDate(date)}</span>}
                </div>
              );
            })}
          </div>
        </ClinicalCard>
      </Section>

      {/* Allergies — Doctor only */}
      <Section id="allergies" show={showAllergies && allergies.length > 0}>
        <ClinicalCard title="Allergies / Intolerances" badge={allergies.length} badgeColor={WARN}>
          <div style={{ display: 'flex', flexDirection: 'column' }}>
            {allergies.map((a: any, i: number) => {
              const substance = bestDisplay(a.code);
              const reaction  = a.reaction?.[0]?.manifestation?.[0]?.text ?? bestDisplay(a.reaction?.[0]?.manifestation?.[0]);
              const severity  = a.criticality ?? a.reaction?.[0]?.severity;
              return (
                <div key={i} style={{ padding: '8px 0', borderBottom: `1px solid ${BORDER}`, display: 'flex', alignItems: 'center', gap: 10, fontSize: 13 }}>
                  <span style={{ width: 6, height: 6, borderRadius: 3, background: severity === 'high' || severity === 'severe' ? WARN : '#E0A400', flexShrink: 0 }} />
                  <span style={{ fontWeight: 500, color: TEXT }}>{substance}</span>
                  {reaction && <span style={{ color: MUTED, fontSize: 12 }}>— {reaction}</span>}
                  {severity && <span style={{ marginLeft: 'auto', fontSize: 11, color: severity === 'high' || severity === 'severe' ? WARN : '#A86A00', fontWeight: 600 }}>{severity}</span>}
                </div>
              );
            })}
          </div>
        </ClinicalCard>
      </Section>

      {/* Adverse Events — Doctor only */}
      <Section id="adverse-events" show={showAdverseEvents && adverse.length > 0}>
        <ClinicalCard title="Adverse Events" badge={adverse.length} badgeColor={WARN}>
          <div style={{ display: 'flex', flexDirection: 'column' }}>
            {adverse.map((ae: any, i: number) => (
              <div key={i} style={{ padding: '8px 0', borderBottom: `1px solid ${BORDER}`, fontSize: 13 }}>
                <div style={{ color: TEXT }}>{bestDisplay(ae.event)}</div>
                {ae.suspectEntity?.[0]?.instance?.display && (
                  <div style={{ fontSize: 12, color: MUTED, marginTop: 2 }}>Caused by: {ae.suspectEntity[0].instance.display}</div>
                )}
              </div>
            ))}
          </div>
        </ClinicalCard>
      </Section>

    </div>
  );
}

import { User, Clock, Stethoscope, Pill, FlaskConical, AlertTriangle, Activity, Heart } from 'lucide-react';

// --- Helpers ---

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
  const composed = [[...(n.given ?? [])].join(' '), n.family].filter(Boolean).join(' ');
  return composed || n.text || '—';
}

function fmtDate(s?: string): string {
  if (!s) return '—';
  try {
    return new Date(s).toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: 'numeric' });
  } catch { return s; }
}

function fmtDateTime(s?: string): string {
  if (!s) return '—';
  try {
    return new Date(s).toLocaleString('en-GB', {
      day: '2-digit', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit',
    });
  } catch { return s; }
}

function calcAge(birthDate?: string): string {
  if (!birthDate) return '';
  try {
    const birth = new Date(birthDate);
    const today = new Date();
    let age = today.getFullYear() - birth.getFullYear();
    const m = today.getMonth() - birth.getMonth();
    if (m < 0 || (m === 0 && today.getDate() < birth.getDate())) age--;
    return `${age} yrs`;
  } catch { return ''; }
}

function encounterPeriod(enc: any): { start?: string; end?: string } {
  // FHIR R5 uses actualPeriod; R4 uses period
  const p = enc?.actualPeriod ?? enc?.period;
  return { start: p?.start, end: p?.end };
}

function encounterDuration(enc: any): string {
  const { start: s, end: e } = encounterPeriod(enc);
  if (!s || !e) return '—';
  const hrs = (new Date(e).getTime() - new Date(s).getTime()) / 3_600_000;
  if (hrs < 24) return `${Math.round(hrs)}h (day-hospital)`;
  const days = Math.round(hrs / 24);
  return `${days} day${days !== 1 ? 's' : ''} (inpatient)`;
}

function encounterClass(enc: any): string {
  // FHIR R5: class is an array of CodeableConcepts
  const cls = Array.isArray(enc?.class) ? enc.class[0] : enc?.class;
  return (cls?.code || cls?.coding?.[0]?.code || '').toUpperCase() || '—';
}

// --- Sub-components ---

function SectionCard({
  title, icon, accent, children,
}: {
  title: string; icon: React.ReactNode; accent: string; children: React.ReactNode;
}) {
  return (
    <div className="glass-panel rounded-xl overflow-hidden border border-slate-700/50">
      <div className={`flex items-center gap-2 px-4 py-2.5 border-b border-slate-700/50 ${accent}`}>
        {icon}
        <span className="text-xs font-semibold tracking-widest uppercase">{title}</span>
      </div>
      <div className="p-4">{children}</div>
    </div>
  );
}

function DL({ label, value, mono = false }: { label: string; value?: string; mono?: boolean }) {
  return (
    <div>
      <dt className="text-[10px] font-medium uppercase tracking-widest text-slate-500">{label}</dt>
      <dd className={`text-sm text-slate-200 mt-0.5 ${mono ? 'font-mono' : ''}`}>{value || '—'}</dd>
    </div>
  );
}

function StatPill({ value, label, color }: { value: string; label: string; color: string }) {
  return (
    <div className="glass-card rounded-lg p-3 text-center border border-slate-700/50 flex-1 min-w-0">
      <div className={`text-2xl font-bold tabular-nums ${color}`}>{value}</div>
      <div className="text-[10px] text-slate-500 uppercase tracking-wider mt-0.5 truncate">{label}</div>
    </div>
  );
}

// --- Main component ---

export function FHIRSummaryPanel({ bundle }: { bundle: any }) {
  const patients    = resources(bundle, 'Patient');
  const encounters  = resources(bundle, 'Encounter');
  const conditions  = resources(bundle, 'Condition');
  const meds        = resources(bundle, 'MedicationRequest');
  const obs         = resources(bundle, 'Observation');
  const procedures  = resources(bundle, 'Procedure');
  const adverse     = resources(bundle, 'AdverseEvent');
  const compositions = resources(bundle, 'Composition');

  const patient   = patients[0];
  const encounter = encounters[0];
  const comp      = compositions[0];

  const loincCode  = comp?.type?.coding?.[0]?.code;
  const docLabel   = loincCode === '34105-7' ? 'Hospital Discharge (DOC_HDR)'
    : loincCode === '34133-9' ? 'Day-Hospital / Ambulatory (DOC_BIS)'
    : loincCode ?? '—';

  const encClass   = encounterClass(encounter);
  const abnormalObs = obs.filter((o: any) => o.interpretation?.[0]?.coding?.[0]?.code === 'A');

  return (
    <div className="space-y-4">
      {/* Stats row */}
      <div className="flex gap-3">
        <StatPill value={loincCode ?? '—'}          label="LOINC type"     color="text-blue-400" />
        <StatPill value={String(bundle?.entry?.length ?? 0)} label="FHIR resources" color="text-teal-400" />
        <StatPill value={encClass}                  label="Encounter"      color={encClass === 'AMB' ? 'text-amber-400' : 'text-violet-400'} />
        <StatPill value={String(conditions.length)} label="Diagnoses"      color="text-rose-400" />
        {abnormalObs.length > 0 && (
          <StatPill value={String(abnormalObs.length)} label="Abnormal labs" color="text-orange-400" />
        )}
      </div>

      {/* Patient + Encounter */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <SectionCard
          title="Patient"
          icon={<User size={14} className="text-blue-400" />}
          accent="bg-blue-500/10 text-blue-300"
        >
          <dl className="grid grid-cols-2 gap-x-6 gap-y-3">
            <div className="col-span-2">
              <DL label="Full Name" value={patientName(patient)} />
            </div>
            <DL label="Date of Birth" value={fmtDate(patient?.birthDate)} />
            <DL label="Age"           value={calcAge(patient?.birthDate)} />
            <DL label="Gender"        value={patient?.gender ? capitalize(patient.gender) : undefined} />
            <DL label="Blood Group"   value={patient?.extension?.find((x: any) => x.url?.includes('blood'))?.valueString} />
            {(patient?.identifier ?? []).slice(0, 2).map((id: any, i: number) => (
              <DL key={i} label={shortSystem(id.system)} value={id.value} mono />
            ))}
          </dl>
        </SectionCard>

        <SectionCard
          title="Encounter"
          icon={<Clock size={14} className="text-violet-400" />}
          accent="bg-violet-500/10 text-violet-300"
        >
          <dl className="grid grid-cols-2 gap-x-6 gap-y-3">
            <DL label="Admission"  value={fmtDateTime(encounterPeriod(encounter).start)} />
            <DL label="Discharge"  value={fmtDateTime(encounterPeriod(encounter).end)} />
            <div className="col-span-2">
              <DL label="Duration" value={encounterDuration(encounter)} />
            </div>
            <div className="col-span-2">
              <DL label="Document Type" value={docLabel} />
            </div>
          </dl>
        </SectionCard>
      </div>

      {/* Diagnoses */}
      {conditions.length > 0 && (
        <SectionCard
          title={`Clinical Diagnoses — ${conditions.length}`}
          icon={<Stethoscope size={14} className="text-rose-400" />}
          accent="bg-rose-500/10 text-rose-300"
        >
          <div className="space-y-1.5">
            {conditions.map((cond: any, i: number) => {
              const display = bestDisplay(cond.code);
              const snomed  = getCode(cond.code, 'snomed');
              const icd10   = getCode(cond.code, 'icd-10') ?? getCode(cond.code, 'icd10');
              const isPrimary = i === 0;
              return (
                <div
                  key={i}
                  className="flex items-start gap-3 p-2.5 rounded-lg bg-slate-800/40 hover:bg-slate-800/70 transition-colors"
                >
                  <span className={`shrink-0 mt-0.5 text-[10px] font-bold px-2 py-0.5 rounded-full ${
                    isPrimary
                      ? 'bg-rose-500/20 text-rose-300 border border-rose-500/30'
                      : 'bg-slate-700/60 text-slate-400 border border-slate-600/30'
                  }`}>
                    {isPrimary ? 'PRI' : 'SEC'}
                  </span>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm text-slate-100 leading-snug">{display}</p>
                    <div className="flex gap-1.5 mt-1 flex-wrap">
                      {snomed && (
                        <CodeBadge label="SNOMED" value={snomed} color="blue" />
                      )}
                      {icd10 && (
                        <CodeBadge label="ICD-10" value={icd10} color="amber" />
                      )}
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </SectionCard>
      )}

      {/* Medications + Labs */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {meds.length > 0 && (
          <SectionCard
            title={`Medications — ${meds.length}`}
            icon={<Pill size={14} className="text-teal-400" />}
            accent="bg-teal-500/10 text-teal-300"
          >
            <div className="space-y-1.5">
              {meds.map((med: any, i: number) => {
                const name   = bestDisplay(med.medicationCodeableConcept);
                const atc    = getCode(med.medicationCodeableConcept, 'atc') ?? getCode(med.medicationCodeableConcept, 'whocc');
                const dosage = med.dosageInstruction?.[0]?.text;
                return (
                  <div key={i} className="flex items-start gap-2 p-2.5 rounded-lg bg-slate-800/40">
                    <Heart size={12} className="text-teal-500 mt-1 shrink-0" />
                    <div className="flex-1 min-w-0">
                      <p className="text-sm text-slate-200 truncate">{name}</p>
                      {dosage && <p className="text-xs text-slate-400 mt-0.5 truncate">{dosage}</p>}
                    </div>
                    {atc && <CodeBadge label="ATC" value={atc} color="teal" />}
                  </div>
                );
              })}
            </div>
          </SectionCard>
        )}

        {obs.length > 0 && (
          <SectionCard
            title={`Lab Results — ${obs.length}${abnormalObs.length ? ` · ${abnormalObs.length} ⚑ abnormal` : ''}`}
            icon={<FlaskConical size={14} className="text-amber-400" />}
            accent="bg-amber-500/10 text-amber-300"
          >
            <div className="space-y-1 max-h-72 overflow-y-auto custom-scrollbar">
              {obs.slice(0, 20).map((o: any, i: number) => {
                const name     = bestDisplay(o.code);
                const val      = o.valueQuantity?.value;
                const unit     = o.valueQuantity?.unit ?? '';
                const loinc    = getCode(o.code, 'loinc');
                const isAbnorm = o.interpretation?.[0]?.coding?.[0]?.code === 'A';
                return (
                  <div
                    key={i}
                    className={`flex items-center gap-2 px-2.5 py-1.5 rounded-lg text-xs ${
                      isAbnorm ? 'bg-red-500/10 border border-red-500/20' : 'bg-slate-800/40'
                    }`}
                  >
                    {isAbnorm && <AlertTriangle size={11} className="text-red-400 shrink-0" />}
                    <span className={`flex-1 truncate ${isAbnorm ? 'text-red-200' : 'text-slate-300'}`}>
                      {name}
                    </span>
                    {val !== undefined && (
                      <span className={`font-mono tabular-nums shrink-0 ${isAbnorm ? 'text-red-300 font-semibold' : 'text-slate-200'}`}>
                        {val} {unit}
                      </span>
                    )}
                    {loinc && <span className="font-mono text-slate-600 shrink-0">{loinc}</span>}
                  </div>
                );
              })}
              {obs.length > 20 && (
                <p className="text-center text-xs text-slate-600 pt-1">+{obs.length - 20} more</p>
              )}
            </div>
          </SectionCard>
        )}
      </div>

      {/* Procedures */}
      {procedures.length > 0 && (
        <SectionCard
          title={`Procedures — ${procedures.length}`}
          icon={<Activity size={14} className="text-emerald-400" />}
          accent="bg-emerald-500/10 text-emerald-300"
        >
          <div className="space-y-1.5">
            {procedures.map((proc: any, i: number) => {
              const name = bestDisplay(proc.code);
              const date = proc.performedDateTime ?? proc.performedPeriod?.start;
              const site = proc.bodySite?.[0] ? bestDisplay(proc.bodySite[0]) : null;
              return (
                <div key={i} className="flex items-start gap-3 p-2.5 rounded-lg bg-slate-800/40">
                  <Activity size={12} className="text-emerald-500 mt-0.5 shrink-0" />
                  <div className="flex-1 min-w-0">
                    <p className="text-sm text-slate-200">{name}</p>
                    <div className="flex gap-3 mt-0.5 text-xs text-slate-500">
                      {date && <span>{fmtDate(date)}</span>}
                      {site && <span>{site}</span>}
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </SectionCard>
      )}

      {/* Adverse Events */}
      {adverse.length > 0 && (
        <SectionCard
          title={`Adverse Events — ${adverse.length}`}
          icon={<AlertTriangle size={14} className="text-orange-400" />}
          accent="bg-orange-500/10 text-orange-300"
        >
          <div className="space-y-1.5">
            {adverse.map((ae: any, i: number) => (
              <div key={i} className="p-2.5 rounded-lg bg-orange-500/5 border border-orange-500/15">
                <p className="text-sm text-slate-200">{bestDisplay(ae.event)}</p>
                {ae.suspectEntity?.[0]?.instance?.display && (
                  <p className="text-xs text-slate-400 mt-0.5">
                    Caused by: {ae.suspectEntity[0].instance.display}
                  </p>
                )}
              </div>
            ))}
          </div>
        </SectionCard>
      )}
    </div>
  );
}

// --- Tiny helpers ---

function CodeBadge({ label, value, color }: { label: string; value: string; color: 'blue' | 'amber' | 'teal' }) {
  const cls = {
    blue:  'text-blue-400 bg-blue-500/10 border-blue-500/20',
    amber: 'text-amber-400 bg-amber-500/10 border-amber-500/20',
    teal:  'text-teal-400 bg-teal-500/10 border-teal-500/20',
  }[color];
  return (
    <span className={`inline-flex items-center gap-1 text-[10px] font-mono border rounded px-1.5 py-0.5 ${cls}`}>
      <span className="opacity-60">{label}</span>
      {value}
    </span>
  );
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

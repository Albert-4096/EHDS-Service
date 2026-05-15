import React, { useCallback, useState } from 'react';
import { UploadCloud, FileText, ShieldCheck, Lock, Zap, FileSearch, Brain, Boxes } from 'lucide-react';
import { motion } from 'framer-motion';

interface UploadDropzoneProps {
  onFileSelect: (file: File, isAnonymized: boolean) => void;
}

export function UploadDropzone({ onFileSelect }: UploadDropzoneProps) {
  const [isDragActive, setIsDragActive] = useState(false);
  const [usePillar2, setUsePillar2] = useState(false);

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
        const file = e.dataTransfer.files[0];
        if (file.type === 'application/pdf') onFileSelect(file, usePillar2);
        else alert('Please upload a PDF file.');
      }
    },
    [onFileSelect, usePillar2]
  );

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    e.preventDefault();
    if (e.target.files?.[0]) onFileSelect(e.target.files[0], usePillar2);
  };

  return (
    <div className="w-full max-w-4xl mx-auto pt-10 pb-4 flex flex-col items-center eu-bg">
      {/* Hero */}
      <motion.div
        initial={{ opacity: 0, y: 24 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
        className="text-center mb-10 px-4"
      >
        <div className="inline-flex items-center gap-2 text-xs font-medium text-blue-400 bg-blue-500/10 border border-blue-500/20 px-3 py-1.5 rounded-full mb-5">
          <span className="w-1.5 h-1.5 rounded-full bg-blue-400 animate-pulse" />
          EU 2025/327 · EEHRxF · HL7 FHIR R4
        </div>
        <h1 className="text-4xl sm:text-5xl font-bold mb-4 leading-tight">
          <span className="gradient-text">EHDS Medical</span>
          <br />
          <span className="text-slate-100">Data Pipeline</span>
        </h1>
        <p className="text-slate-400 text-base sm:text-lg max-w-2xl mx-auto leading-relaxed">
          Upload Romanian hospital discharge summaries. Our zero-trust AI pipeline extracts,
          validates, and converts them to{' '}
          <span className="text-slate-200 font-medium">HL7 FHIR R4 bundles</span> compliant
          with the European Health Data Space regulation.
        </p>
      </motion.div>

      {/* Pillar toggle */}
      <motion.div
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, delay: 0.1 }}
        className="flex items-center gap-1 mb-5 bg-slate-800/60 p-1 rounded-xl border border-slate-700/50"
      >
        <PillarButton
          active={!usePillar2}
          onClick={() => setUsePillar2(false)}
          icon={<ShieldCheck size={14} />}
          label="Pillar 1 — Direct Care"
          activeColor="bg-blue-600"
        />
        <PillarButton
          active={usePillar2}
          onClick={() => setUsePillar2(true)}
          icon={<Lock size={14} />}
          label="Pillar 2 — Anonymized"
          activeColor="bg-teal-600"
        />
      </motion.div>

      {/* Pillar description */}
      <motion.p
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ duration: 0.3, delay: 0.15 }}
        className="text-xs text-slate-500 mb-5 text-center"
      >
        {usePillar2
          ? 'Temporal shifting (Δt) + PII stripping + k-anonymity generalization for research use'
          : 'Full fidelity record for authorized healthcare professionals in direct patient care'}
      </motion.p>

      {/* Dropzone */}
      <motion.div
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, delay: 0.2 }}
        className="w-full"
      >
        <div
          onDragEnter={handleDrag}
          onDragLeave={handleDrag}
          onDragOver={handleDrag}
          onDrop={handleDrop}
          className={`w-full relative rounded-2xl glass-panel p-12 text-center cursor-pointer transition-all duration-200 ${
            isDragActive
              ? 'border-teal-500/70 bg-teal-500/5 shadow-[0_0_40px_rgba(20,184,166,0.15)]'
              : 'border-slate-700/60 hover:border-blue-500/40 hover:bg-slate-800/30'
          }`}
        >
          <input
            type="file"
            accept=".pdf"
            className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
            onChange={handleChange}
          />
          <div className="flex flex-col items-center justify-center gap-4 pointer-events-none">
            <div
              className={`p-5 rounded-2xl transition-all duration-200 ${
                isDragActive ? 'bg-teal-500/20 text-teal-400' : 'bg-slate-800/80 text-blue-400'
              }`}
            >
              {isDragActive ? <FileText size={44} /> : <UploadCloud size={44} />}
            </div>
            <div>
              <p className="text-xl font-semibold text-white mb-1.5">
                {isDragActive ? 'Drop PDF here' : 'Click or drag PDF to upload'}
              </p>
              <p className="text-slate-400 text-sm">
                Supports digital and scanned Romanian clinical documents
              </p>
            </div>
            <div className="flex gap-3 text-xs text-slate-500 mt-1">
              <DocTypePill label="Bilet de Externare" subtitle="DOC_HDR" />
              <DocTypePill label="Bilet de Ieșire" subtitle="DOC_BIS" />
            </div>
          </div>
        </div>
      </motion.div>

      {/* Feature cards */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, delay: 0.35 }}
        className="grid grid-cols-1 sm:grid-cols-3 gap-4 w-full mt-8"
      >
        <FeatureCard
          icon={<FileSearch size={20} className="text-blue-400" />}
          title="Smart Extraction"
          description="9-stage pipeline: OCR, zone detection, LLM-powered clinical narrative parsing via Claude."
          color="blue"
        />
        <FeatureCard
          icon={<Brain size={20} className="text-purple-400" />}
          title="AI-Powered NLP"
          description="Separates current visit from longitudinal history. Extracts TNM, ECOG, procedures, devices."
          color="purple"
        />
        <FeatureCard
          icon={<Boxes size={20} className="text-teal-400" />}
          title="FHIR R4 Assembly"
          description="Produces validated FHIR bundles with SNOMED CT, LOINC, ATC, and UCUM terminologies."
          color="teal"
        />
      </motion.div>

      {/* Pipeline stages strip */}
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ duration: 0.5, delay: 0.5 }}
        className="flex items-center gap-1 mt-8 flex-wrap justify-center"
      >
        {PIPELINE_STAGES.map((stage, i) => (
          <React.Fragment key={stage}>
            <span className="text-xs text-slate-600 font-mono bg-slate-800/50 px-2 py-0.5 rounded">
              {stage}
            </span>
            {i < PIPELINE_STAGES.length - 1 && (
              <Zap size={10} className="text-slate-700" />
            )}
          </React.Fragment>
        ))}
      </motion.div>
    </div>
  );
}

const PIPELINE_STAGES = [
  'PDF Forensics',
  'Text Extract',
  'Classify',
  'Zone Detect',
  'Structured Fields',
  'Labs',
  'Checkboxes',
  'LLM Epicriza',
  'Medications',
  'FHIR Assembly',
  'Bundle',
  'HAPI Upload',
];

function PillarButton({
  active,
  onClick,
  icon,
  label,
  activeColor,
}: {
  active: boolean;
  onClick: () => void;
  icon: React.ReactNode;
  label: string;
  activeColor: string;
}) {
  return (
    <button
      onClick={onClick}
      className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all ${
        active ? `${activeColor} text-white shadow-lg` : 'text-slate-400 hover:text-white'
      }`}
    >
      {icon}
      {label}
    </button>
  );
}

function FeatureCard({
  icon,
  title,
  description,
  color,
}: {
  icon: React.ReactNode;
  title: string;
  description: string;
  color: 'blue' | 'purple' | 'teal';
}) {
  const border = {
    blue: 'border-blue-500/20 hover:border-blue-500/40',
    purple: 'border-purple-500/20 hover:border-purple-500/40',
    teal: 'border-teal-500/20 hover:border-teal-500/40',
  }[color];

  const bg = {
    blue: 'bg-blue-500/8',
    purple: 'bg-purple-500/8',
    teal: 'bg-teal-500/8',
  }[color];

  return (
    <div className={`glass-panel rounded-xl p-4 border ${border} ${bg} transition-all duration-200`}>
      <div className="mb-2">{icon}</div>
      <h3 className="text-sm font-semibold text-slate-100 mb-1">{title}</h3>
      <p className="text-xs text-slate-400 leading-relaxed">{description}</p>
    </div>
  );
}

function DocTypePill({ label, subtitle }: { label: string; subtitle: string }) {
  return (
    <span className="flex items-center gap-1.5 bg-slate-800/60 border border-slate-700/60 px-2.5 py-1 rounded-full">
      <FileText size={11} className="text-slate-500" />
      <span className="text-slate-400">{label}</span>
      <span className="text-slate-600 font-mono">{subtitle}</span>
    </span>
  );
}

import React, { useCallback, useState } from 'react';
import { UploadCloud, FileText } from 'lucide-react';
import { motion } from 'framer-motion';

interface UploadDropzoneProps {
  onFileSelect: (file: File, isAnonymized: boolean) => void;
}

export function UploadDropzone({ onFileSelect }: UploadDropzoneProps) {
  const [isDragActive, setIsDragActive] = useState(false);
  const [usePillar2, setUsePillar2] = useState(true);

  const handleDrag = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") {
      setIsDragActive(true);
    } else if (e.type === "dragleave") {
      setIsDragActive(false);
    }
  }, []);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragActive(false);

    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      const file = e.dataTransfer.files[0];
      if (file.type === "application/pdf") {
        onFileSelect(file, usePillar2);
      } else {
        alert("Please upload a PDF file.");
      }
    }
  }, [onFileSelect, usePillar2]);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    e.preventDefault();
    if (e.target.files && e.target.files[0]) {
      onFileSelect(e.target.files[0], usePillar2);
    }
  };

  return (
    <div className="w-full max-w-3xl mx-auto mt-12 flex flex-col items-center">
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
        className="w-full text-center mb-8"
      >
        <h1 className="text-4xl font-bold mb-4 bg-gradient-to-r from-blue-400 to-teal-400 bg-clip-text text-transparent">
          EHDS Data Factory
        </h1>
        <p className="text-gray-400 text-lg max-w-xl mx-auto">
          Upload Romanian hospital discharge summaries. Our zero-trust pipeline will extract, structure, and convert them to FHIR R4 standard.
        </p>
      </motion.div>

      <div className="flex items-center space-x-4 mb-6 bg-slate-800/50 p-2 rounded-xl border border-slate-700/50">
        <button
          onClick={() => setUsePillar2(false)}
          className={`px-4 py-2 rounded-lg text-sm font-medium transition-all ${!usePillar2 ? 'bg-blue-600 text-white shadow-lg' : 'text-gray-400 hover:text-white'}`}
        >
          Primary Use (Direct Care)
        </button>
        <button
          onClick={() => setUsePillar2(true)}
          className={`px-4 py-2 rounded-lg text-sm font-medium transition-all ${usePillar2 ? 'bg-teal-600 text-white shadow-lg' : 'text-gray-400 hover:text-white'}`}
        >
          Secondary Use (Anonymized)
        </button>
      </div>

      <motion.div
        onDragEnter={handleDrag}
        onDragLeave={handleDrag}
        onDragOver={handleDrag}
        onDrop={handleDrop}
        whileHover={{ scale: 1.02 }}
        whileTap={{ scale: 0.98 }}
        className={`w-full relative rounded-2xl glass-panel p-12 text-center cursor-pointer transition-all ${
          isDragActive ? 'border-teal-500 bg-teal-500/10' : 'border-slate-700 hover:border-blue-500/50 hover:bg-slate-800/50'
        }`}
      >
        <input
          type="file"
          accept=".pdf"
          className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
          onChange={handleChange}
        />
        
        <div className="flex flex-col items-center justify-center space-y-4 pointer-events-none">
          <div className={`p-4 rounded-full ${isDragActive ? 'bg-teal-500/20 text-teal-400' : 'bg-slate-800 text-blue-400'}`}>
            {isDragActive ? <FileText size={48} /> : <UploadCloud size={48} />}
          </div>
          
          <div>
            <p className="text-xl font-semibold text-white mb-2">
              {isDragActive ? "Drop PDF here" : "Click or drag PDF to upload"}
            </p>
            <p className="text-slate-400 text-sm">
              Supports digital and scanned clinical documents
            </p>
          </div>
        </div>
      </motion.div>
    </div>
  );
}

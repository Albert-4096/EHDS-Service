import { useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import { ShieldCheck, BrainCircuit, Search, Database } from 'lucide-react';

const STEPS = [
  { id: 1, text: "Extracting document forensics & text...", icon: Search },
  { id: 2, text: "Classifying and splitting clinical zones...", icon: ShieldCheck },
  { id: 3, text: "Querying LLM for deep medical narrative...", icon: BrainCircuit },
  { id: 4, text: "Assembling FHIR R4 Bundle...", icon: Database }
];

export function LoadingScreen() {
  const [activeStep, setActiveStep] = useState(0);

  useEffect(() => {
    // Simulate pipeline stages progressing over a ~8-12 second window
    const interval = setInterval(() => {
      setActiveStep(prev => (prev < STEPS.length - 1 ? prev + 1 : prev));
    }, 2500);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="w-full max-w-2xl mx-auto mt-20 flex flex-col items-center">
      <motion.div
        initial={{ opacity: 0, scale: 0.9 }}
        animate={{ opacity: 1, scale: 1 }}
        className="glass-panel p-10 rounded-2xl w-full border border-teal-500/30 shadow-[0_0_40px_rgba(20,184,166,0.15)]"
      >
        <div className="flex justify-center mb-8">
          <div className="relative">
            <div className="absolute inset-0 bg-teal-500 blur-xl opacity-50 rounded-full animate-pulse" />
            <BrainCircuit size={64} className="text-teal-400 relative z-10 animate-bounce" />
          </div>
        </div>

        <h2 className="text-2xl font-bold text-center text-white mb-8">
          Processing Pipeline Active
        </h2>

        <div className="space-y-6">
          {STEPS.map((step, index) => {
            const Icon = step.icon;
            const isActive = index === activeStep;
            const isPast = index < activeStep;

            return (
              <div key={step.id} className="flex items-center space-x-4">
                <div className={`w-10 h-10 rounded-full flex items-center justify-center transition-all duration-500 ${
                  isActive ? 'bg-teal-500/20 text-teal-400 border border-teal-500 shadow-[0_0_15px_rgba(20,184,166,0.5)]' :
                  isPast ? 'bg-blue-500/20 text-blue-400 border border-blue-500/50' :
                  'bg-slate-800 text-slate-600'
                }`}>
                  <Icon size={20} />
                </div>
                
                <div className="flex-1">
                  <p className={`font-medium transition-colors duration-500 ${
                    isActive ? 'text-teal-400' :
                    isPast ? 'text-gray-300' :
                    'text-slate-600'
                  }`}>
                    {step.text}
                  </p>
                  
                  <div className="h-1 w-full bg-slate-800 mt-2 rounded-full overflow-hidden">
                    {(isActive || isPast) && (
                      <motion.div 
                        className={`h-full ${isPast ? 'bg-blue-500' : 'bg-teal-500'}`}
                        initial={{ width: isPast ? "100%" : "0%" }}
                        animate={{ width: isPast ? "100%" : "100%" }}
                        transition={{ duration: isPast ? 0 : 2.5, ease: "linear" }}
                      />
                    )}
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </motion.div>
    </div>
  );
}

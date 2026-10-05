import React from 'react'
import { Activity, ShieldAlert, Cpu, Terminal } from 'lucide-react'
import { useQuery } from '@tanstack/react-query'
import { api } from '../../services/api'

export default function Navbar() {
  const { data: health } = useQuery({
    queryKey: ['health'],
    queryFn: api.getHealth,
    refetchInterval: 15000,
  })

  return (
    <header className="h-16 border-b border-surface-600/70 bg-surface-900/80 backdrop-blur-md px-6 flex items-center justify-between sticky top-0 z-30">
      <div className="flex items-center gap-3">
        <div className="flex items-center justify-center w-9 h-9 rounded-lg bg-gradient-to-br from-primary-500 to-accent-cyan text-white shadow-glow-primary">
          <Cpu className="w-5 h-5" />
        </div>
        <div>
          <div className="flex items-center gap-2">
            <span className="font-bold text-sm tracking-wider uppercase text-slate-100 font-mono">
              IFMD Platform
            </span>
            <span className="text-[10px] bg-primary-950/80 text-primary-300 border border-primary-800/60 px-2 py-0.5 rounded-full font-mono font-medium">
              v0.1.0 Research
            </span>
          </div>
          <p className="text-xs text-slate-400 hidden sm:block">
            Industrial Failure Mechanism Discovery & Hypothesis Ranking
          </p>
        </div>
      </div>

      <div className="flex items-center gap-4">
        {/* System Health Status */}
        <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-surface-800/80 border border-surface-600/60 text-xs font-mono">
          <div
            className={`w-2 h-2 rounded-full animate-pulse ${
              health?.status === 'ok' ? 'bg-accent-green' : 'bg-accent-red'
            }`}
          />
          <span className="text-slate-300">
            {health?.status === 'ok' ? 'System Online' : 'Connecting...'}
          </span>
          {health?.database && (
            <span className="text-slate-500 border-l border-surface-600 pl-2">
              DB: {health.database}
            </span>
          )}
        </div>

        {/* Mode Tag */}
        <div className="hidden md:flex items-center gap-1.5 px-2.5 py-1 rounded bg-surface-700/50 text-[11px] font-mono text-slate-400 border border-surface-600/40">
          <Terminal className="w-3.5 h-3.5 text-accent-cyan" />
          <span>Heterogeneous Pipeline</span>
        </div>
      </div>
    </header>
  )
}

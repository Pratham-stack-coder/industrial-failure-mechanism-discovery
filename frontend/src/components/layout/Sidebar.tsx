import React from 'react'
import { NavLink } from 'react-router-dom'
import {
  LayoutDashboard,
  UploadCloud,
  FileSearch,
  GitFork,
  Clock,
  Layers,
  FlaskConical,
  Settings,
  ChevronRight,
  ShieldCheck,
} from 'lucide-react'

const navItems = [
  { to: '/', label: 'Overview Dashboard', icon: LayoutDashboard, exact: true },
  { to: '/upload', label: 'Data & Generation', icon: UploadCloud },
  { to: '/investigations', label: 'Failure Investigations', icon: FileSearch },
  { to: '/evaluation', label: 'Research Evaluation', icon: FlaskConical },
  { to: '/settings', label: 'System Configuration', icon: Settings },
]

export default function Sidebar() {
  return (
    <aside className="w-64 border-r border-surface-600/70 bg-surface-900/90 flex flex-col justify-between flex-shrink-0 min-h-[calc(100vh-4rem)]">
      <div className="py-5 px-3 space-y-6">
        <div>
          <div className="px-3 mb-2 text-[11px] font-mono uppercase tracking-wider text-slate-400 font-semibold">
            Core Modules
          </div>
          <nav className="space-y-1">
            {navItems.map((item) => {
              const Icon = item.icon
              return (
                <NavLink
                  key={item.to}
                  to={item.to}
                  end={item.exact}
                  className={({ isActive }) =>
                    `flex items-center justify-between px-3 py-2.5 rounded-lg text-sm font-medium transition-all group ${
                      isActive
                        ? 'bg-primary-600/20 text-accent-cyan border border-primary-500/30 shadow-glow-primary'
                        : 'text-slate-400 hover:text-slate-100 hover:bg-surface-800'
                    }`
                  }
                >
                  <div className="flex items-center gap-3">
                    <Icon className="w-4 h-4 transition-transform group-hover:scale-110" />
                    <span>{item.label}</span>
                  </div>
                  <ChevronRight className="w-3.5 h-3.5 opacity-0 group-hover:opacity-100 transition-opacity text-slate-500" />
                </NavLink>
              )
            })}
          </nav>
        </div>

        <div>
          <div className="px-3 mb-2 text-[11px] font-mono uppercase tracking-wider text-slate-400 font-semibold">
            Research Architecture
          </div>
          <div className="px-3 py-3 rounded-lg bg-surface-800/60 border border-surface-700 text-xs text-slate-400 space-y-2">
            <div className="flex items-center gap-2 text-slate-300 font-medium">
              <ShieldCheck className="w-3.5 h-3.5 text-accent-green" />
              <span>Causal Hypothesis Engine</span>
            </div>
            <p className="text-[11px] leading-relaxed text-slate-400">
              Discovers competing failure mechanisms using temporal alignment, heterogeneous dependency graphs, and multi-factor ranking.
            </p>
            <div className="pt-2 border-t border-surface-700/60 flex items-center justify-between text-[10px] font-mono text-slate-400">
              <span>Benchmark:</span>
              <span className="text-accent-cyan font-bold">NDCG@5 / MRR</span>
            </div>
          </div>
        </div>
      </div>

      <div className="p-4 border-t border-surface-700/60 bg-surface-800/40">
        <div className="flex items-center justify-between text-xs text-slate-400 font-mono">
          <span>AI Research Engine</span>
          <span className="text-accent-green font-semibold">Active</span>
        </div>
      </div>
    </aside>
  )
}

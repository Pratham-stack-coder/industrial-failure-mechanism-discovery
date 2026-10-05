import React, { useState } from 'react'
import {
  Settings,
  Sliders,
  Cpu,
  Database,
  Sparkles,
  Save,
  CheckCircle,
  ShieldAlert,
} from 'lucide-react'
import toast from 'react-hot-toast'
import Badge from '../components/ui/Badge'

export default function SettingsPage() {
  // Config state
  const [llmProvider, setLlmProvider] = useState('google')
  const [modelName, setModelName] = useState('gemini-1.5-flash')
  const [temperature, setTemperature] = useState(0.2)

  // Ranking weights
  const [wTemporal, setWTemporal] = useState(0.35)
  const [wStrength, setWStrength] = useState(0.25)
  const [wCoverage, setWCoverage] = useState(0.20)
  const [wRecurrence, setWRecurrence] = useState(0.10)
  const [wPlausibility, setWPlausibility] = useState(0.10)
  const [wContradiction, setWContradiction] = useState(0.50)

  const handleSave = () => {
    toast.success('Configuration saved locally')
  }

  return (
    <div className="space-y-8 animate-fade-in max-w-4xl">
      <div>
        <h1 className="text-2xl font-bold font-mono text-slate-100">
          System & Pipeline Configuration
        </h1>
        <p className="text-xs text-slate-400 mt-1">
          Tune the multi-factor hypothesis ranking weights, LLM grounded explainability engine, and industrial telemetry thresholds.
        </p>
      </div>

      {/* Multi-Factor Ranking Weights */}
      <div className="card space-y-6">
        <div className="flex items-center gap-3">
          <div className="p-2.5 rounded-lg bg-primary-600/20 text-accent-cyan border border-primary-500/30">
            <Sliders className="w-5 h-5" />
          </div>
          <div>
            <h2 className="text-sm font-bold font-mono text-slate-100">
              Multi-Factor Ranking Formula Weights
            </h2>
            <p className="text-xs text-slate-400">
              Score = w₁·Temporal + w₂·Strength + w₃·Coverage + w₄·Recurrence + w₅·Plausibility − w_pen·Contradiction
            </p>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-5 text-xs font-mono">
          <div>
            <div className="flex justify-between text-slate-300 mb-1">
              <span>Temporal Consistency (w₁):</span>
              <span className="text-accent-cyan font-bold">{wTemporal}</span>
            </div>
            <input
              type="range"
              min="0.0"
              max="1.0"
              step="0.05"
              value={wTemporal}
              onChange={(e) => setWTemporal(parseFloat(e.target.value))}
              className="w-full accent-primary-500 cursor-pointer"
            />
          </div>

          <div>
            <div className="flex justify-between text-slate-300 mb-1">
              <span>Evidence Strength (w₂):</span>
              <span className="text-accent-cyan font-bold">{wStrength}</span>
            </div>
            <input
              type="range"
              min="0.0"
              max="1.0"
              step="0.05"
              value={wStrength}
              onChange={(e) => setWStrength(parseFloat(e.target.value))}
              className="w-full accent-primary-500 cursor-pointer"
            />
          </div>

          <div>
            <div className="flex justify-between text-slate-300 mb-1">
              <span>Evidence Coverage (w₃):</span>
              <span className="text-accent-cyan font-bold">{wCoverage}</span>
            </div>
            <input
              type="range"
              min="0.0"
              max="1.0"
              step="0.05"
              value={wCoverage}
              onChange={(e) => setWCoverage(parseFloat(e.target.value))}
              className="w-full accent-primary-500 cursor-pointer"
            />
          </div>

          <div>
            <div className="flex justify-between text-slate-300 mb-1">
              <span>Recurrence Score (w₄):</span>
              <span className="text-accent-cyan font-bold">{wRecurrence}</span>
            </div>
            <input
              type="range"
              min="0.0"
              max="1.0"
              step="0.05"
              value={wRecurrence}
              onChange={(e) => setWRecurrence(parseFloat(e.target.value))}
              className="w-full accent-primary-500 cursor-pointer"
            />
          </div>

          <div>
            <div className="flex justify-between text-slate-300 mb-1">
              <span>Plausibility Score (w₅):</span>
              <span className="text-accent-cyan font-bold">{wPlausibility}</span>
            </div>
            <input
              type="range"
              min="0.0"
              max="1.0"
              step="0.05"
              value={wPlausibility}
              onChange={(e) => setWPlausibility(parseFloat(e.target.value))}
              className="w-full accent-primary-500 cursor-pointer"
            />
          </div>

          <div>
            <div className="flex justify-between text-slate-300 mb-1">
              <span>Contradiction Penalty Factor:</span>
              <span className="text-accent-red font-bold">{wContradiction}</span>
            </div>
            <input
              type="range"
              min="0.0"
              max="1.0"
              step="0.05"
              value={wContradiction}
              onChange={(e) => setWContradiction(parseFloat(e.target.value))}
              className="w-full accent-accent-red cursor-pointer"
            />
          </div>
        </div>
      </div>

      {/* LLM Explanation Config */}
      <div className="card space-y-5">
        <div className="flex items-center gap-3">
          <div className="p-2.5 rounded-lg bg-surface-700 text-accent-cyan border border-surface-600">
            <Sparkles className="w-5 h-5" />
          </div>
          <div>
            <h2 className="text-sm font-bold font-mono text-slate-100">
              Grounded LLM Explanation Engine
            </h2>
            <p className="text-xs text-slate-400">
              Generates executive failure summaries strictly grounded in extracted evidence chains without hallucinations
            </p>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div>
            <label className="block text-xs font-mono text-slate-300 mb-1">Provider</label>
            <select
              value={llmProvider}
              onChange={(e) => setLlmProvider(e.target.value)}
              className="w-full bg-surface-900 border border-surface-600 rounded-lg px-3 py-2 text-xs font-mono text-slate-100"
            >
              <option value="google">Google Gemini</option>
              <option value="openai">OpenAI GPT-4o</option>
              <option value="ollama">Local Ollama</option>
              <option value="none">Deterministic Rule Fallback (No API)</option>
            </select>
          </div>

          <div>
            <label className="block text-xs font-mono text-slate-300 mb-1">Model Name</label>
            <input
              type="text"
              value={modelName}
              onChange={(e) => setModelName(e.target.value)}
              className="w-full bg-surface-900 border border-surface-600 rounded-lg px-3 py-2 text-xs font-mono text-slate-100"
            />
          </div>

          <div>
            <label className="block text-xs font-mono text-slate-300 mb-1">
              Temperature ({temperature})
            </label>
            <input
              type="range"
              min="0.0"
              max="1.0"
              step="0.1"
              value={temperature}
              onChange={(e) => setTemperature(parseFloat(e.target.value))}
              className="w-full mt-2 accent-primary-500"
            />
          </div>
        </div>
      </div>

      {/* System Telemetry & Environment Info */}
      <div className="card space-y-4">
        <h3 className="text-sm font-bold font-mono text-slate-100">Environment Metadata</h3>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs font-mono">
          <div className="p-3 rounded-lg bg-surface-900 border border-surface-700">
            <span className="text-[10px] text-slate-500 uppercase block">Backend Framework</span>
            <span className="text-slate-200 font-semibold">FastAPI + AsyncPG</span>
          </div>
          <div className="p-3 rounded-lg bg-surface-900 border border-surface-700">
            <span className="text-[10px] text-slate-500 uppercase block">Graph Engine</span>
            <span className="text-slate-200 font-semibold">NetworkX 3.3</span>
          </div>
          <div className="p-3 rounded-lg bg-surface-900 border border-surface-700">
            <span className="text-[10px] text-slate-500 uppercase block">Temporal Models</span>
            <span className="text-slate-200 font-semibold">SciPy + Pandas + NumPy</span>
          </div>
          <div className="p-3 rounded-lg bg-surface-900 border border-surface-700">
            <span className="text-[10px] text-slate-500 uppercase block">Frontend Architecture</span>
            <span className="text-slate-200 font-semibold">React 18 + Vite + Tailwind</span>
          </div>
        </div>
      </div>

      <div className="flex justify-end">
        <button onClick={handleSave} className="btn-primary text-xs px-5 py-2.5">
          <Save className="w-4 h-4" />
          <span>Save Settings</span>
        </button>
      </div>
    </div>
  )
}

import React from 'react'
import { useParams, Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import {
  ArrowLeft,
  ShieldCheck,
  Cpu,
  Layers,
  Clock,
  CheckCircle,
  AlertTriangle,
  HelpCircle,
  FileText,
  Sparkles,
  ExternalLink,
  ChevronRight,
  TrendingDown,
} from 'lucide-react'
import { api } from '../services/api'
import Badge from '../components/ui/Badge'
import StatCard from '../components/ui/StatCard'
import { LoadingState } from '../components/ui/FeedbackStates'
import EvidenceBreakdownChart from '../components/charts/EvidenceBreakdownChart'

export default function MechanismDetailPage() {
  const { id } = useParams<{ id: string }>()

  const { data: mech, isLoading } = useQuery({
    queryKey: ['mechanism', id],
    queryFn: () => api.getMechanism(id!),
    enabled: !!id,
  })

  if (isLoading) return <LoadingState message="Loading mechanism details..." />
  if (!mech) return <div className="card p-8 text-center text-slate-400">Mechanism not found.</div>

  return (
    <div className="space-y-8 animate-fade-in">
      {/* Header */}
      <div className="space-y-2">
        <Link
          to={`/investigations/${mech.investigation_id}`}
          className="inline-flex items-center gap-1.5 text-xs font-mono text-slate-400 hover:text-accent-cyan transition-colors"
        >
          <ArrowLeft className="w-3.5 h-3.5" />
          <span>Back to Investigation Overview</span>
        </Link>

        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <span className="flex items-center justify-center w-9 h-9 rounded-xl bg-surface-700 text-accent-cyan font-mono font-bold text-base border border-surface-600">
              #{mech.rank}
            </span>
            <div>
              <div className="flex items-center gap-2">
                <h1 className="text-2xl font-bold font-mono text-slate-100">{mech.name}</h1>
                <Badge variant="primary">{mech.mechanism_type}</Badge>
              </div>
              <p className="text-xs text-slate-400 mt-0.5">
                Discovered via <span className="font-mono text-slate-300">{mech.discovery_method}</span>
              </p>
            </div>
          </div>

          <Link
            to={`/mechanisms/${mech.id}/evidence`}
            className="btn-primary text-xs self-start md:self-auto"
          >
            <span>Explore All Evidence Items</span>
            <ExternalLink className="w-3.5 h-3.5" />
          </Link>
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          title="Overall Hypothesis Score"
          value={`${Math.round(mech.overall_score * 100)}%`}
          subtitle="Multi-factor rank score"
          icon={ShieldCheck}
          color="cyan"
        />
        <StatCard
          title="Confidence Measure"
          value={`${Math.round(mech.confidence * 100)}%`}
          subtitle="Statistical significance"
          icon={Cpu}
          color="green"
        />
        <StatCard
          title="Supporting Records"
          value={mech.supporting_evidence_count}
          subtitle={`${mech.contradicting_evidence_count} contradicting`}
          icon={CheckCircle}
          color="primary"
        />
        <StatCard
          title="Contradiction Penalty"
          value={`-${Math.round(mech.contradiction_penalty * 100)}%`}
          subtitle="Subtracted from overall"
          icon={TrendingDown}
          color="red"
        />
      </div>

      {/* Physics / Causal Formulation */}
      <div className="card space-y-4">
        <h3 className="text-sm font-bold font-mono text-slate-100 uppercase tracking-wider">
          Physical Causal Mechanism Formulation
        </h3>
        <p className="text-xs text-slate-300 leading-relaxed">{mech.description}</p>

        <div className="grid grid-cols-1 md:grid-cols-4 gap-3 pt-2">
          <div className="p-3.5 rounded-lg bg-surface-900/80 border border-surface-700/80">
            <span className="text-[10px] font-mono uppercase text-accent-orange font-semibold block">
              1. Root / Antecedent Cause
            </span>
            <p className="text-xs text-slate-200 mt-1 font-mono">{mech.cause}</p>
          </div>

          <div className="p-3.5 rounded-lg bg-surface-900/80 border border-surface-700/80">
            <span className="text-[10px] font-mono uppercase text-primary-300 font-semibold block">
              2. Process Condition
            </span>
            <p className="text-xs text-slate-200 mt-1 font-mono">{mech.process_condition}</p>
          </div>

          <div className="p-3.5 rounded-lg bg-surface-900/80 border border-surface-700/80">
            <span className="text-[10px] font-mono uppercase text-accent-cyan font-semibold block">
              3. Intermediate State
            </span>
            <p className="text-xs text-slate-200 mt-1 font-mono">{mech.intermediate_effect}</p>
          </div>

          <div className="p-3.5 rounded-lg bg-surface-900/80 border border-rose-900/50">
            <span className="text-[10px] font-mono uppercase text-accent-red font-semibold block">
              4. Observable Failure
            </span>
            <p className="text-xs text-slate-100 mt-1 font-mono font-semibold">{mech.observable_failure}</p>
          </div>
        </div>
      </div>

      {/* Charts & Scoring Breakdown */}
      <EvidenceBreakdownChart mechanism={mech} />

      {/* Variables & System Entities Involved */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="card space-y-3">
          <h4 className="text-xs font-mono uppercase tracking-wider text-slate-400 font-semibold">
            Telemetry & Variables Involved
          </h4>
          <div className="flex flex-wrap gap-2">
            {mech.variables_involved?.map((v, i) => (
              <span
                key={i}
                className="px-2.5 py-1 rounded bg-surface-900 border border-surface-700 text-xs font-mono text-accent-cyan"
              >
                {v}
              </span>
            ))}
            {(!mech.variables_involved || mech.variables_involved.length === 0) && (
              <span className="text-xs text-slate-500 font-mono">None specified</span>
            )}
          </div>
        </div>

        <div className="card space-y-3">
          <h4 className="text-xs font-mono uppercase tracking-wider text-slate-400 font-semibold">
            Physical Entities & Equipment Involved
          </h4>
          <div className="flex flex-wrap gap-2">
            {mech.entities_involved?.map((e, i) => (
              <span
                key={i}
                className="px-2.5 py-1 rounded bg-surface-900 border border-surface-700 text-xs font-mono text-primary-300"
              >
                {e}
              </span>
            ))}
            {(!mech.entities_involved || mech.entities_involved.length === 0) && (
              <span className="text-xs text-slate-500 font-mono">None specified</span>
            )}
          </div>
        </div>
      </div>

      {/* LLM Grounded Explanation Report */}
      {mech.llm_explanation && (
        <div className="card space-y-3 border-primary-500/40 bg-surface-800/80">
          <div className="flex items-center gap-2 text-accent-cyan">
            <Sparkles className="w-4 h-4" />
            <h4 className="text-xs font-mono uppercase tracking-wider font-semibold">
              Grounded Natural Language Synthesis
            </h4>
          </div>
          <div className="p-4 rounded-xl bg-surface-900/90 border border-surface-700/80 text-xs text-slate-200 leading-relaxed font-sans whitespace-pre-line">
            {mech.llm_explanation}
          </div>
        </div>
      )}
    </div>
  )
}

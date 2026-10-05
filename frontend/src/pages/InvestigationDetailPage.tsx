import React from 'react'
import { useParams, Link } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  FileSearch,
  Clock,
  GitFork,
  Play,
  ArrowLeft,
  CheckCircle,
  AlertTriangle,
  Layers,
  ChevronRight,
  ExternalLink,
  ShieldCheck,
  RefreshCw,
  Sparkles,
} from 'lucide-react'
import toast from 'react-hot-toast'
import { api } from '../services/api'
import Badge from '../components/ui/Badge'
import StatCard from '../components/ui/StatCard'
import { LoadingState } from '../components/ui/FeedbackStates'
import MechanismRankingChart from '../components/charts/MechanismRankingChart'

export default function InvestigationDetailPage() {
  const { id } = useParams<{ id: string }>()
  const queryClient = useQueryClient()

  const { data: inv, isLoading: loadingInv } = useQuery({
    queryKey: ['investigation', id],
    queryFn: () => api.getInvestigation(id!),
    enabled: !!id,
    refetchInterval: (query) => (query.state.data?.status === 'running' ? 3000 : false),
  })

  const { data: mechsData, isLoading: loadingMechs } = useQuery({
    queryKey: ['investigation-mechanisms', id],
    queryFn: () => api.getInvestigationMechanisms(id!),
    enabled: !!id && inv?.status === 'completed',
  })

  const runMutation = useMutation({
    mutationFn: () => api.runInvestigation(id!),
    onSuccess: () => {
      toast.success('Investigation pipeline started in background')
      queryClient.invalidateQueries({ queryKey: ['investigation', id] })
    },
    onError: (err: any) => {
      toast.error(err.response?.data?.detail || 'Failed to start pipeline')
    },
  })

  if (loadingInv) return <LoadingState message="Loading investigation record..." />
  if (!inv) return <div className="card p-8 text-center text-slate-400">Investigation not found.</div>

  const mechanisms = mechsData?.mechanisms || []

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Back button & Title */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div className="space-y-1">
          <Link
            to="/investigations"
            className="inline-flex items-center gap-1.5 text-xs font-mono text-slate-400 hover:text-accent-cyan transition-colors"
          >
            <ArrowLeft className="w-3.5 h-3.5" />
            <span>Back to Investigations</span>
          </Link>
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-bold font-mono text-slate-100">{inv.name}</h1>
            <Badge
              variant={
                inv.status === 'completed'
                  ? 'success'
                  : inv.status === 'running'
                  ? 'info'
                  : inv.status === 'failed'
                  ? 'danger'
                  : 'neutral'
              }
            >
              {inv.status}
            </Badge>
          </div>
          <p className="text-xs text-slate-400">{inv.description || 'Target industrial failure investigation'}</p>
        </div>

        {/* Quick action buttons */}
        <div className="flex items-center gap-2">
          {inv.status === 'created' && (
            <button
              onClick={() => runMutation.mutate()}
              disabled={runMutation.isPending}
              className="btn-primary text-xs"
            >
              <Play className="w-3.5 h-3.5" />
              <span>Execute Pipeline</span>
            </button>
          )}

          {inv.status === 'completed' && (
            <>
              <Link
                to={`/investigations/${id}/timeline`}
                className="px-3 py-2 rounded-lg bg-surface-700 hover:bg-surface-600 text-xs font-mono text-slate-200 transition-colors flex items-center gap-1.5 border border-surface-600"
              >
                <Clock className="w-3.5 h-3.5 text-accent-cyan" />
                <span>Timeline</span>
              </Link>
              <Link
                to={`/investigations/${id}/graph`}
                className="px-3 py-2 rounded-lg bg-primary-600/20 text-primary-300 hover:bg-primary-600/30 border border-primary-500/30 text-xs font-mono transition-colors flex items-center gap-1.5"
              >
                <GitFork className="w-3.5 h-3.5" />
                <span>Relationship Graph</span>
              </Link>
            </>
          )}
        </div>
      </div>

      {/* Meta Stats Bar */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          title="Investigation Status"
          value={inv.status.toUpperCase()}
          subtitle={`Dataset ID: ${inv.dataset_id.slice(0, 8)}...`}
          icon={FileSearch}
          color={inv.status === 'completed' ? 'green' : 'primary'}
        />
        <StatCard
          title="Candidate Mechanisms"
          value={inv.candidate_count || mechanisms.length}
          subtitle="Formulated hypotheses"
          icon={Layers}
          color="cyan"
        />
        <StatCard
          title="Analysis Window"
          value={`${new Date(inv.analysis_start_time).toLocaleDateString()}`}
          subtitle={`to ${new Date(inv.analysis_end_time).toLocaleDateString()}`}
          icon={Clock}
          color="orange"
        />
        <StatCard
          title="Top Hypothesis Score"
          value={
            inv.top_mechanism_score
              ? `${Math.round(inv.top_mechanism_score * 100)}%`
              : mechanisms[0]
              ? `${Math.round(mechanisms[0].overall_score * 100)}%`
              : 'N/A'
          }
          subtitle={inv.top_mechanism_name || mechanisms[0]?.name || 'Pending run'}
          icon={ShieldCheck}
          color="green"
        />
      </div>

      {/* Running State */}
      {inv.status === 'running' && (
        <div className="card p-8 text-center space-y-4 border-primary-500/40">
          <div className="flex justify-center">
            <RefreshCw className="w-10 h-10 text-primary-400 animate-spin" />
          </div>
          <div>
            <h3 className="text-base font-bold font-mono text-slate-100">
              Pipeline Execution in Progress
            </h3>
            <p className="text-xs text-slate-400 mt-1 max-w-md mx-auto">
              Extracting temporal features, constructing heterogeneous entity-event graph, mining candidate mechanism paths, and executing multi-factor hypothesis ranking.
            </p>
          </div>
        </div>
      )}

      {/* Completed State: Comparison Chart & Mechanisms */}
      {inv.status === 'completed' && (
        <div className="space-y-6">
          {mechanisms.length > 0 && (
            <MechanismRankingChart mechanisms={mechanisms} />
          )}

          <div>
            <div className="flex items-center justify-between mb-3">
              <h2 className="text-lg font-bold font-mono text-slate-100">
                Ranked Candidate Failure Mechanisms
              </h2>
              <span className="text-xs font-mono text-slate-400">
                Sorted by Multi-Factor Objective Score
              </span>
            </div>

            {loadingMechs ? (
              <LoadingState message="Loading candidate mechanisms..." />
            ) : mechanisms.length === 0 ? (
              <div className="card p-8 text-center text-slate-400 text-xs">
                No candidate mechanisms discovered for the given temporal window.
              </div>
            ) : (
              <div className="space-y-4">
                {mechanisms.map((mech) => (
                  <div
                    key={mech.id}
                    className="card p-5 hover:border-primary-500/40 transition-all space-y-4"
                  >
                    <div className="flex flex-col md:flex-row md:items-start justify-between gap-4">
                      <div className="space-y-1">
                        <div className="flex items-center gap-3">
                          <span className="flex items-center justify-center w-7 h-7 rounded-lg bg-surface-700 text-accent-cyan font-mono font-bold text-xs border border-surface-600">
                            #{mech.rank}
                          </span>
                          <h3 className="text-base font-bold text-slate-100 font-mono">
                            {mech.name}
                          </h3>
                          <Badge variant="primary">{mech.mechanism_type}</Badge>
                        </div>
                        <p className="text-xs text-slate-300 pt-1 leading-relaxed">
                          {mech.description}
                        </p>
                      </div>

                      {/* Score Badge Pill */}
                      <div className="flex items-center gap-3 bg-surface-900/80 border border-surface-700/80 px-4 py-2 rounded-xl self-start">
                        <div className="text-right">
                          <div className="text-[10px] font-mono uppercase text-slate-400">
                            Overall Score
                          </div>
                          <div className="text-lg font-bold font-mono text-accent-cyan">
                            {Math.round(mech.overall_score * 100)}%
                          </div>
                        </div>
                        <div className="h-8 w-[1px] bg-surface-700" />
                        <div className="text-right">
                          <div className="text-[10px] font-mono uppercase text-slate-400">
                            Confidence
                          </div>
                          <div className="text-lg font-bold font-mono text-accent-green">
                            {Math.round(mech.confidence * 100)}%
                          </div>
                        </div>
                      </div>
                    </div>

                    {/* Causal Chain Breadcrumbs */}
                    <div className="p-3 rounded-lg bg-surface-900/60 border border-surface-700/60 text-xs">
                      <div className="text-[10px] font-mono text-slate-400 uppercase tracking-wider mb-1.5">
                        Proposed Causal Sequence:
                      </div>
                      <div className="flex flex-wrap items-center gap-2 font-mono text-slate-300">
                        <span className="px-2 py-0.5 rounded bg-surface-800 border border-surface-700 text-accent-orange">
                          {mech.cause}
                        </span>
                        <ChevronRight className="w-3.5 h-3.5 text-slate-500" />
                        <span className="px-2 py-0.5 rounded bg-surface-800 border border-surface-700 text-slate-200">
                          {mech.process_condition}
                        </span>
                        <ChevronRight className="w-3.5 h-3.5 text-slate-500" />
                        <span className="px-2 py-0.5 rounded bg-surface-800 border border-surface-700 text-slate-200">
                          {mech.intermediate_effect}
                        </span>
                        <ChevronRight className="w-3.5 h-3.5 text-slate-500" />
                        <span className="px-2 py-0.5 rounded bg-surface-800 border border-surface-700 text-accent-red font-semibold">
                          {mech.observable_failure}
                        </span>
                      </div>
                    </div>

                    {/* Evidence Tags & Link */}
                    <div className="flex flex-wrap items-center justify-between gap-3 pt-1 border-t border-surface-700/60 text-xs font-mono">
                      <div className="flex items-center gap-3">
                        <span className="text-accent-green flex items-center gap-1">
                          <CheckCircle className="w-3.5 h-3.5" />
                          <span>{mech.supporting_evidence_count} Supporting</span>
                        </span>
                        <span className="text-accent-red flex items-center gap-1">
                          <AlertTriangle className="w-3.5 h-3.5" />
                          <span>{mech.contradicting_evidence_count} Contradicting</span>
                        </span>
                        <span className="text-slate-400">
                          {mech.missing_evidence_count} Missing
                        </span>
                      </div>

                      <div className="flex items-center gap-2">
                        <Link
                          to={`/mechanisms/${mech.id}`}
                          className="px-3 py-1.5 rounded-lg bg-surface-700 hover:bg-surface-600 text-slate-200 transition-colors flex items-center gap-1"
                        >
                          <span>Full Analysis</span>
                          <ChevronRight className="w-3.5 h-3.5" />
                        </Link>
                        <Link
                          to={`/mechanisms/${mech.id}/evidence`}
                          className="px-3 py-1.5 rounded-lg bg-primary-600/20 text-accent-cyan hover:bg-primary-600/30 border border-primary-500/30 transition-colors flex items-center gap-1"
                        >
                          <span>Evidence Explorer</span>
                          <ExternalLink className="w-3.5 h-3.5" />
                        </Link>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}

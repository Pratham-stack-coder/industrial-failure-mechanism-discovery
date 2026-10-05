import React, { useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import {
  FileText,
  ArrowLeft,
  Filter,
  CheckCircle,
  AlertTriangle,
  HelpCircle,
  Search,
  Database,
  Calendar,
  Layers,
  ArrowUpRight,
  TrendingDown,
} from 'lucide-react'
import { api } from '../services/api'
import Badge from '../components/ui/Badge'
import { LoadingState, EmptyState } from '../components/ui/FeedbackStates'
import type { MechanismEvidence } from '../types'

export default function EvidenceExplorerPage() {
  const { id } = useParams<{ id: string }>()
  const [activePolarity, setActivePolarity] = useState<string>('all')
  const [search, setSearch] = useState<string>('')

  const { data: mech } = useQuery({
    queryKey: ['mechanism', id],
    queryFn: () => api.getMechanism(id!),
    enabled: !!id,
  })

  const { data: evidenceData, isLoading } = useQuery({
    queryKey: ['mechanism-evidence', id, activePolarity],
    queryFn: () => api.getMechanismEvidence(id!, activePolarity === 'all' ? undefined : activePolarity),
    enabled: !!id,
  })

  const evidenceItems: MechanismEvidence[] = evidenceData?.evidence || []

  const filtered = evidenceItems.filter((e) => {
    if (!search) return true
    return (
      e.description.toLowerCase().includes(search.toLowerCase()) ||
      e.evidence_type.toLowerCase().includes(search.toLowerCase()) ||
      e.source_table.toLowerCase().includes(search.toLowerCase())
    )
  })

  if (isLoading) return <LoadingState message="Extracting heterogeneous evidence records..." />

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="space-y-1">
        <Link
          to={`/mechanisms/${id}`}
          className="inline-flex items-center gap-1.5 text-xs font-mono text-slate-400 hover:text-accent-cyan transition-colors"
        >
          <ArrowLeft className="w-3.5 h-3.5" />
          <span>Back to Mechanism Details</span>
        </Link>
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-2xl font-bold font-mono text-slate-100">
                Evidence Explorer
              </h1>
              {mech && (
                <span className="text-xs font-mono px-2.5 py-1 rounded bg-primary-950/80 text-primary-300 border border-primary-800">
                  Hypothesis #{mech.rank}: {mech.name}
                </span>
              )}
            </div>
            <p className="text-xs text-slate-400 mt-1">
              Audit trail of concrete data points supporting, refuting, or missing for this failure mechanism hypothesis.
            </p>
          </div>
        </div>
      </div>

      {/* Filter Tabs and Search Bar */}
      <div className="card p-3 flex flex-wrap items-center justify-between gap-4 bg-surface-800/80">
        <div className="flex flex-wrap items-center gap-2">
          {['all', 'supporting', 'contradicting', 'missing', 'inconclusive'].map((pol) => (
            <button
              key={pol}
              onClick={() => setActivePolarity(pol)}
              className={`px-3 py-1.5 rounded-lg text-xs font-mono capitalize transition-colors ${
                activePolarity === pol
                  ? 'bg-primary-600 text-white font-semibold'
                  : 'bg-surface-700 text-slate-300 hover:bg-surface-600'
              }`}
            >
              {pol}
            </button>
          ))}
        </div>

        <div className="relative min-w-[220px]">
          <Search className="w-3.5 h-3.5 text-slate-500 absolute left-3 top-2.5" />
          <input
            type="text"
            placeholder="Search evidence descriptions..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full bg-surface-900 border border-surface-600 rounded-lg pl-8 pr-3 py-1.5 text-xs text-slate-200 focus:outline-none focus:border-primary-500 font-mono"
          />
        </div>
      </div>

      {/* Evidence Cards List */}
      {filtered.length === 0 ? (
        <EmptyState
          icon={<FileText className="w-8 h-8" />}
          title="No evidence items found"
          description="There is no recorded evidence matching your selected polarity filter or query."
        />
      ) : (
        <div className="space-y-3">
          {filtered.map((item) => {
            const isSupporting = item.polarity === 'supporting'
            const isContradicting = item.polarity === 'contradicting'
            const isMissing = item.polarity === 'missing'

            return (
              <div
                key={item.id}
                className="card p-4 hover:border-surface-500 transition-all space-y-3"
              >
                <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-3">
                  <div className="space-y-1">
                    <div className="flex items-center gap-2">
                      <Badge
                        variant={
                          isSupporting
                            ? 'success'
                            : isContradicting
                            ? 'danger'
                            : isMissing
                            ? 'warning'
                            : 'neutral'
                        }
                      >
                        {item.polarity}
                      </Badge>
                      <span className="font-mono text-xs font-semibold text-slate-300">
                        {item.evidence_type}
                      </span>
                    </div>
                    <p className="text-xs text-slate-200 leading-relaxed font-sans pt-1">
                      {item.description}
                    </p>
                  </div>

                  {/* Strength Bar */}
                  <div className="bg-surface-900/80 border border-surface-700 p-2.5 rounded-lg text-right min-w-[140px] self-start">
                    <div className="text-[10px] font-mono uppercase text-slate-400">
                      Evidence Strength
                    </div>
                    <div className="text-sm font-bold font-mono text-accent-cyan">
                      {Math.round(item.strength * 100)}%
                    </div>
                    <div className="w-full bg-surface-700 h-1.5 rounded-full mt-1 overflow-hidden">
                      <div
                        className={`h-full rounded-full ${
                          isSupporting
                            ? 'bg-accent-green'
                            : isContradicting
                            ? 'bg-accent-red'
                            : 'bg-accent-yellow'
                        }`}
                        style={{ width: `${Math.round(item.strength * 100)}%` }}
                      />
                    </div>
                  </div>
                </div>

                {/* Quantitative Details */}
                <div className="flex flex-wrap items-center gap-4 text-[11px] font-mono text-slate-400 bg-surface-900/60 p-2.5 rounded-lg border border-surface-700/60">
                  <div className="flex items-center gap-1.5">
                    <Database className="w-3.5 h-3.5 text-slate-500" />
                    <span>Table: {item.source_table}</span>
                  </div>

                  {item.source_timestamp && (
                    <div className="flex items-center gap-1.5">
                      <Calendar className="w-3.5 h-3.5 text-slate-500" />
                      <span>{new Date(item.source_timestamp).toLocaleString()}</span>
                    </div>
                  )}

                  {item.measured_value !== undefined && item.measured_value !== null && (
                    <div>
                      <span>Measured: </span>
                      <span className="text-slate-200 font-semibold">{item.measured_value}</span>
                    </div>
                  )}

                  {item.expected_value !== undefined && item.expected_value !== null && (
                    <div>
                      <span>Expected: </span>
                      <span className="text-slate-200 font-semibold">{item.expected_value}</span>
                    </div>
                  )}

                  {item.deviation !== undefined && item.deviation !== null && (
                    <div>
                      <span>Deviation: </span>
                      <span
                        className={`font-semibold ${
                          item.deviation > 0 ? 'text-accent-red' : 'text-accent-green'
                        }`}
                      >
                        {item.deviation > 0 ? `+${item.deviation}` : item.deviation}
                      </span>
                    </div>
                  )}
                </div>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}

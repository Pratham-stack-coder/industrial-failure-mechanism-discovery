import React, { useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import {
  Clock,
  ArrowLeft,
  Filter,
  AlertTriangle,
  Wrench,
  Activity,
  Layers,
  CheckCircle2,
  Calendar,
  ChevronDown,
  ArrowUpDown,
} from 'lucide-react'
import { api } from '../services/api'
import Badge from '../components/ui/Badge'
import { LoadingState, EmptyState } from '../components/ui/FeedbackStates'
import type { TimelineEvent } from '../types'

export default function TimelinePage() {
  const { id } = useParams<{ id: string }>()
  const [filterType, setFilterType] = useState<string>('all')
  const [sortAsc, setSortAsc] = useState<boolean>(true)

  const { data: timelineData, isLoading } = useQuery({
    queryKey: ['investigation-timeline', id],
    queryFn: () => api.getInvestigationTimeline(id!),
    enabled: !!id,
  })

  if (isLoading) return <LoadingState message="Reconstructing temporal event sequence..." />

  const rawEvents = timelineData?.timeline || []

  // Unique event types for filter
  const eventTypes = Array.from(new Set(rawEvents.map((e) => e.event_type)))

  const filtered = rawEvents
    .filter((e) => filterType === 'all' || e.event_type === filterType)
    .sort((a, b) => {
      const diff = new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime()
      return sortAsc ? diff : -diff
    })

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div className="space-y-1">
          <Link
            to={`/investigations/${id}`}
            className="inline-flex items-center gap-1.5 text-xs font-mono text-slate-400 hover:text-accent-cyan transition-colors"
          >
            <ArrowLeft className="w-3.5 h-3.5" />
            <span>Back to Investigation</span>
          </Link>
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-bold font-mono text-slate-100">
              Temporal Event Timeline
            </h1>
            <Badge variant="primary">{rawEvents.length} Events Logged</Badge>
          </div>
          <p className="text-xs text-slate-400">
            Reconstructed chronological sequence of process changes, telemetry anomalies, maintenance actions, and quality measurements preceding failure.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={() => setSortAsc(!sortAsc)}
            className="px-3 py-2 rounded-lg bg-surface-700 hover:bg-surface-600 text-xs font-mono text-slate-200 flex items-center gap-2 border border-surface-600 transition-colors"
          >
            <ArrowUpDown className="w-3.5 h-3.5" />
            <span>{sortAsc ? 'Earliest First' : 'Latest First'}</span>
          </button>
        </div>
      </div>

      {/* Filters Bar */}
      <div className="card p-3 flex flex-wrap items-center gap-2 bg-surface-800/80">
        <span className="text-xs font-mono text-slate-400 flex items-center gap-1.5 mr-2">
          <Filter className="w-3.5 h-3.5" />
          <span>Filter by Type:</span>
        </span>
        <button
          onClick={() => setFilterType('all')}
          className={`px-2.5 py-1 rounded-md text-xs font-mono transition-colors ${
            filterType === 'all'
              ? 'bg-primary-600 text-white font-semibold'
              : 'bg-surface-700 text-slate-300 hover:bg-surface-600'
          }`}
        >
          All ({rawEvents.length})
        </button>
        {eventTypes.map((t) => (
          <button
            key={t}
            onClick={() => setFilterType(t)}
            className={`px-2.5 py-1 rounded-md text-xs font-mono transition-colors ${
              filterType === t
                ? 'bg-primary-600 text-white font-semibold'
                : 'bg-surface-700 text-slate-300 hover:bg-surface-600'
            }`}
          >
            {t} ({rawEvents.filter((e) => e.event_type === t).length})
          </button>
        ))}
      </div>

      {/* Timeline Stream */}
      {filtered.length === 0 ? (
        <EmptyState
          icon={<Clock className="w-8 h-8" />}
          title="No timeline events found"
          description="There are no events matching the selected filter criteria."
        />
      ) : (
        <div className="relative border-l-2 border-surface-700 ml-4 pl-6 space-y-6">
          {filtered.map((ev, index) => {
            const isCritical = ev.severity === 'critical' || ev.severity === 'high'
            return (
              <div key={ev.id || index} className="relative group">
                {/* Node icon / indicator */}
                <div
                  className={`absolute -left-[35px] top-1.5 w-6 h-6 rounded-full border-2 flex items-center justify-center transition-transform group-hover:scale-125 ${
                    isCritical
                      ? 'border-accent-red bg-rose-950 text-accent-red shadow-glow-danger'
                      : 'border-primary-500 bg-surface-900 text-accent-cyan shadow-glow-primary'
                  }`}
                >
                  <div className="w-2 h-2 rounded-full bg-current" />
                </div>

                <div className="card p-4 hover:border-surface-500 transition-all space-y-2">
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-surface-700/60 pb-2">
                    <div className="flex items-center gap-2">
                      <span className="font-mono font-bold text-xs text-slate-200">
                        {ev.name || ev.event_type}
                      </span>
                      <Badge
                        variant={
                          isCritical
                            ? 'danger'
                            : ev.severity === 'medium'
                            ? 'warning'
                            : 'neutral'
                        }
                      >
                        {ev.severity || 'info'}
                      </Badge>
                      <span className="text-[11px] font-mono text-slate-400 bg-surface-900 px-2 py-0.5 rounded border border-surface-700">
                        {ev.entity_type}: {ev.entity_id}
                      </span>
                    </div>

                    <div className="text-[11px] font-mono text-slate-400 flex items-center gap-1.5">
                      <Calendar className="w-3 h-3 text-slate-500" />
                      <span>{new Date(ev.timestamp).toLocaleString()}</span>
                    </div>
                  </div>

                  <p className="text-xs text-slate-300 leading-relaxed">
                    {ev.description}
                  </p>

                  {ev.metadata && Object.keys(ev.metadata).length > 0 && (
                    <div className="flex flex-wrap gap-2 pt-1 text-[11px] font-mono text-slate-400">
                      {Object.entries(ev.metadata).map(([k, v]) => (
                        <span
                          key={k}
                          className="bg-surface-900 px-2 py-0.5 rounded border border-surface-700/60"
                        >
                          <span className="text-slate-500">{k}:</span>{' '}
                          <span className="text-slate-300">{String(v)}</span>
                        </span>
                      ))}
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

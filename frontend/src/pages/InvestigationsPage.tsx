import React, { useState } from 'react'
import { Link } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  FileSearch,
  Plus,
  Play,
  Clock,
  CheckCircle,
  AlertTriangle,
  RefreshCw,
  GitFork,
  Layers,
  ArrowRight,
} from 'lucide-react'
import toast from 'react-hot-toast'
import { api } from '../services/api'
import Badge from '../components/ui/Badge'
import { LoadingState, EmptyState } from '../components/ui/FeedbackStates'

export default function InvestigationsPage() {
  const queryClient = useQueryClient()
  const [showModal, setShowModal] = useState(false)
  const [filterStatus, setFilterStatus] = useState<string>('all')

  // Form state
  const [name, setName] = useState('')
  const [description, setDescription] = useState('')
  const [selectedDatasetId, setSelectedDatasetId] = useState('')
  const [startTime, setStartTime] = useState(
    new Date(Date.now() - 30 * 24 * 60 * 60 * 1000).toISOString().slice(0, 16),
  )
  const [endTime, setEndTime] = useState(new Date().toISOString().slice(0, 16))

  // Fetch datasets for selection
  const { data: datasets } = useQuery({
    queryKey: ['datasets'],
    queryFn: () => api.getDatasets(0, 50),
  })

  // Fetch investigations
  const { data: invData, isLoading, refetch } = useQuery({
    queryKey: ['investigations'],
    queryFn: () => api.getInvestigations(0, 100),
    refetchInterval: 5000, // poll for running status
  })

  // Create investigation mutation
  const createMutation = useMutation({
    mutationFn: async () => {
      const created = await api.createInvestigation({
        name,
        description,
        dataset_id: selectedDatasetId,
        analysis_start_time: new Date(startTime).toISOString(),
        analysis_end_time: new Date(endTime).toISOString(),
      })
      // Automatically trigger pipeline run
      await api.runInvestigation(created.id)
      return created
    },
    onSuccess: () => {
      toast.success('Investigation created & pipeline triggered')
      setShowModal(false)
      setName('')
      setDescription('')
      queryClient.invalidateQueries({ queryKey: ['investigations'] })
    },
    onError: (err: any) => {
      toast.error(err.response?.data?.detail || 'Failed to create investigation')
    },
  })

  // Manual run trigger mutation
  const runMutation = useMutation({
    mutationFn: (id: string) => api.runInvestigation(id),
    onSuccess: () => {
      toast.success('Pipeline execution started in background')
      queryClient.invalidateQueries({ queryKey: ['investigations'] })
    },
    onError: (err: any) => {
      toast.error(err.response?.data?.detail || 'Failed to start pipeline')
    },
  })

  const investigations = invData?.investigations || []
  const filtered =
    filterStatus === 'all'
      ? investigations
      : investigations.filter((i) => i.status === filterStatus)

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold font-mono text-slate-100">
            Failure Investigations
          </h1>
          <p className="text-xs text-slate-400 mt-1">
            Formulate and execute causal discovery pipelines over temporal sensor windows to rank candidate failure mechanisms.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={() => refetch()}
            className="p-2 rounded-lg bg-surface-700 hover:bg-surface-600 text-slate-300 transition-colors"
            title="Refresh list"
          >
            <RefreshCw className="w-4 h-4" />
          </button>
          <button
            onClick={() => {
              if (datasets && datasets.length > 0 && !selectedDatasetId) {
                setSelectedDatasetId(datasets[0].id)
              }
              setShowModal(true)
            }}
            className="btn-primary text-xs"
          >
            <Plus className="w-4 h-4" />
            <span>New Investigation</span>
          </button>
        </div>
      </div>

      {/* Filter Tabs */}
      <div className="flex items-center gap-2 border-b border-surface-700/60 pb-3">
        {['all', 'completed', 'running', 'created', 'failed'].map((st) => (
          <button
            key={st}
            onClick={() => setFilterStatus(st)}
            className={`px-3 py-1.5 rounded-lg text-xs font-mono transition-colors uppercase ${
              filterStatus === st
                ? 'bg-primary-600/30 text-accent-cyan border border-primary-500/40 font-semibold'
                : 'text-slate-400 hover:bg-surface-800 hover:text-slate-200'
            }`}
          >
            {st} ({st === 'all' ? investigations.length : investigations.filter((i) => i.status === st).length})
          </button>
        ))}
      </div>

      {/* List */}
      {isLoading ? (
        <LoadingState message="Loading investigations..." />
      ) : filtered.length === 0 ? (
        <EmptyState
          icon={<FileSearch className="w-8 h-8" />}
          title="No investigations found"
          description="Create a new investigation to start discovering failure mechanisms from temporal sensor & batch logs."
          action={
            <button
              onClick={() => {
                if (datasets && datasets.length > 0) setSelectedDatasetId(datasets[0].id)
                setShowModal(true)
              }}
              className="btn-primary text-xs"
            >
              <Plus className="w-4 h-4" />
              <span>Create First Investigation</span>
            </button>
          }
        />
      ) : (
        <div className="grid grid-cols-1 gap-4">
          {filtered.map((inv) => (
            <div
              key={inv.id}
              className="card p-5 hover:border-surface-500 transition-all flex flex-col md:flex-row md:items-center justify-between gap-5"
            >
              <div className="space-y-2 max-w-2xl">
                <div className="flex items-center gap-3">
                  <h3 className="text-base font-bold text-slate-100 font-mono">
                    {inv.name}
                  </h3>
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

                <p className="text-xs text-slate-300">
                  {inv.description || 'System failure hypothesis search run'}
                </p>

                <div className="flex flex-wrap items-center gap-4 text-xs font-mono text-slate-400 pt-1">
                  <span>
                    Window: {new Date(inv.analysis_start_time).toLocaleDateString()} –{' '}
                    {new Date(inv.analysis_end_time).toLocaleDateString()}
                  </span>
                  <span>Mechanisms: {inv.candidate_count ?? 0}</span>
                  {inv.top_mechanism_name && (
                    <span className="text-accent-cyan font-semibold">
                      Rank 1: {inv.top_mechanism_name} (
                      {Math.round((inv.top_mechanism_score || 0) * 100)}%)
                    </span>
                  )}
                </div>
              </div>

              <div className="flex flex-wrap items-center gap-2 self-end md:self-center">
                {inv.status === 'created' && (
                  <button
                    onClick={() => runMutation.mutate(inv.id)}
                    disabled={runMutation.isPending}
                    className="btn-primary text-xs px-3 py-1.5"
                  >
                    <Play className="w-3.5 h-3.5" />
                    <span>Run Pipeline</span>
                  </button>
                )}

                <Link
                  to={`/investigations/${inv.id}`}
                  className="px-3 py-1.5 rounded-lg bg-surface-700 hover:bg-surface-600 text-xs font-mono text-slate-200 transition-colors"
                >
                  View Details
                </Link>

                {inv.status === 'completed' && (
                  <>
                    <Link
                      to={`/investigations/${inv.id}/timeline`}
                      className="px-3 py-1.5 rounded-lg bg-surface-700 hover:bg-surface-600 text-xs font-mono text-slate-200 transition-colors flex items-center gap-1.5"
                    >
                      <Clock className="w-3.5 h-3.5 text-accent-cyan" />
                      <span>Timeline</span>
                    </Link>
                    <Link
                      to={`/investigations/${inv.id}/graph`}
                      className="px-3 py-1.5 rounded-lg bg-primary-600/20 text-primary-300 hover:bg-primary-600/30 border border-primary-500/30 text-xs font-mono transition-colors flex items-center gap-1.5"
                    >
                      <GitFork className="w-3.5 h-3.5" />
                      <span>Graph</span>
                    </Link>
                  </>
                )}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Create Modal */}
      {showModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm animate-fade-in">
          <div className="card w-full max-w-lg p-6 space-y-4 bg-surface-800 border-surface-600 shadow-2xl">
            <div className="flex items-center justify-between border-b border-surface-700 pb-3">
              <h3 className="text-base font-bold font-mono text-slate-100">
                New Failure Investigation
              </h3>
              <button
                onClick={() => setShowModal(false)}
                className="text-slate-400 hover:text-slate-200 text-sm font-mono"
              >
                ✕
              </button>
            </div>

            <div className="space-y-3">
              <div>
                <label className="block text-xs font-mono text-slate-300 mb-1">
                  Investigation Name *
                </label>
                <input
                  type="text"
                  placeholder="e.g. Investigation - Spindle Thermal Spike & Part Out-of-Spec"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  className="w-full bg-surface-900 border border-surface-600 rounded-lg px-3 py-2 text-xs text-slate-100 focus:outline-none focus:border-primary-500"
                />
              </div>

              <div>
                <label className="block text-xs font-mono text-slate-300 mb-1">
                  Description
                </label>
                <textarea
                  rows={2}
                  placeholder="Engineering context, failure symptoms, or quality excursion details"
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  className="w-full bg-surface-900 border border-surface-600 rounded-lg px-3 py-2 text-xs text-slate-100 focus:outline-none focus:border-primary-500"
                />
              </div>

              <div>
                <label className="block text-xs font-mono text-slate-300 mb-1">
                  Target Dataset *
                </label>
                <select
                  value={selectedDatasetId}
                  onChange={(e) => setSelectedDatasetId(e.target.value)}
                  className="w-full bg-surface-900 border border-surface-600 rounded-lg px-3 py-2 text-xs font-mono text-slate-100 focus:outline-none focus:border-primary-500"
                >
                  {datasets?.map((d) => (
                    <option key={d.id} value={d.id}>
                      {d.name} ({d.source_type} - {d.record_count} records)
                    </option>
                  ))}
                </select>
                {(!datasets || datasets.length === 0) && (
                  <p className="text-[11px] text-accent-red mt-1">
                    No datasets available. Please generate or upload a dataset first.
                  </p>
                )}
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-mono text-slate-300 mb-1">
                    Analysis Start Time
                  </label>
                  <input
                    type="datetime-local"
                    value={startTime}
                    onChange={(e) => setStartTime(e.target.value)}
                    className="w-full bg-surface-900 border border-surface-600 rounded-lg px-3 py-1.5 text-xs font-mono text-slate-100 focus:outline-none focus:border-primary-500"
                  />
                </div>
                <div>
                  <label className="block text-xs font-mono text-slate-300 mb-1">
                    Analysis End Time
                  </label>
                  <input
                    type="datetime-local"
                    value={endTime}
                    onChange={(e) => setEndTime(e.target.value)}
                    className="w-full bg-surface-900 border border-surface-600 rounded-lg px-3 py-1.5 text-xs font-mono text-slate-100 focus:outline-none focus:border-primary-500"
                  />
                </div>
              </div>
            </div>

            <div className="flex items-center justify-end gap-3 pt-3 border-t border-surface-700">
              <button
                onClick={() => setShowModal(false)}
                className="px-4 py-2 rounded-lg bg-surface-700 hover:bg-surface-600 text-xs font-mono text-slate-300"
              >
                Cancel
              </button>
              <button
                onClick={() => createMutation.mutate()}
                disabled={!name || !selectedDatasetId || createMutation.isPending}
                className="btn-primary text-xs"
              >
                {createMutation.isPending ? 'Launching Pipeline...' : 'Create & Run Pipeline'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

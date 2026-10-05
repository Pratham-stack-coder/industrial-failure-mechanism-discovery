import React, { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  UploadCloud,
  Sparkles,
  Database,
  FileText,
  CheckCircle,
  AlertCircle,
  Layers,
  Cpu,
  RefreshCw,
} from 'lucide-react'
import toast from 'react-hot-toast'
import { api } from '../services/api'
import Badge from '../components/ui/Badge'
import { LoadingState } from '../components/ui/FeedbackStates'

export default function DataUploadPage() {
  const queryClient = useQueryClient()

  // Synthetic generator state
  const [nBatches, setNBatches] = useState<number>(500)
  const [randomSeed, setRandomSeed] = useState<number>(42)

  // Upload state
  const [uploadFile, setUploadFile] = useState<File | null>(null)
  const [uploadName, setUploadName] = useState<string>('')
  const [uploadDesc, setUploadDesc] = useState<string>('')

  // Fetch datasets
  const { data: datasets, isLoading: loadingDatasets } = useQuery({
    queryKey: ['datasets'],
    queryFn: () => api.getDatasets(0, 50),
  })

  // Mutation: Generate Synthetic
  const generateMutation = useMutation({
    mutationFn: () => api.generateSyntheticData({ n_batches: nBatches, random_seed: randomSeed }),
    onSuccess: (data) => {
      toast.success(`Synthetic dataset generated (${nBatches} batches)`)
      queryClient.invalidateQueries({ queryKey: ['datasets'] })
    },
    onError: (err: any) => {
      toast.error(err.response?.data?.detail || 'Failed to generate synthetic data')
    },
  })

  // Mutation: Upload File
  const uploadMutation = useMutation({
    mutationFn: () => {
      if (!uploadFile) throw new Error('No file selected')
      const formData = new FormData()
      formData.append('file', uploadFile)
      formData.append('name', uploadName || uploadFile.name)
      if (uploadDesc) formData.append('description', uploadDesc)
      return api.uploadDataset(formData)
    },
    onSuccess: () => {
      toast.success('Dataset uploaded and schema validated successfully')
      setUploadFile(null)
      setUploadName('')
      setUploadDesc('')
      queryClient.invalidateQueries({ queryKey: ['datasets'] })
    },
    onError: (err: any) => {
      toast.error(err.response?.data?.detail || 'Failed to upload dataset')
    },
  })

  return (
    <div className="space-y-8 animate-fade-in">
      <div>
        <h1 className="text-2xl font-bold font-mono text-slate-100">
          Data Ingestion & Benchmark Generation
        </h1>
        <p className="text-xs text-slate-400 mt-1">
          Ingest heterogeneous manufacturing datasets (telemetry, batch logs, maintenance history, quality records) or synthesize controlled benchmark datasets with verified ground-truth mechanisms.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        {/* Synthetic Generator Card */}
        <div className="card space-y-5 border-primary-500/30 bg-surface-800/90">
          <div className="flex items-center gap-3">
            <div className="p-2.5 rounded-lg bg-primary-600/20 text-accent-cyan border border-primary-500/30">
              <Sparkles className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-sm font-bold font-mono text-slate-100">
                Ground-Truth Synthetic Generator
              </h2>
              <p className="text-xs text-slate-400">
                Synthesizes 5 multi-step physical failure mechanisms with known ground truth for scientific benchmarking
              </p>
            </div>
          </div>

          <div className="p-3.5 rounded-lg bg-surface-900/80 border border-surface-700/80 text-xs text-slate-300 space-y-2">
            <span className="font-mono text-accent-cyan font-semibold block">
              Embedded Physical Failure Mechanisms:
            </span>
            <ul className="list-disc list-inside space-y-1 text-slate-400 text-[11px]">
              <li><strong className="text-slate-200">Cooling Degradation:</strong> Coolant flow decline → spindle temp rise → thermal expansion failure</li>
              <li><strong className="text-slate-200">Material Contamination:</strong> Impurity lot → feed force spikes → accelerated tool wear</li>
              <li><strong className="text-slate-200">Wear Acceleration:</strong> Missed PM → vibration harmonic increase → bearing seizure</li>
              <li><strong className="text-slate-200">Process Drift:</strong> Pressure regulator drift → dimension variance → dimensional defect</li>
              <li><strong className="text-slate-200">Thermal Expansion:</strong> Ambient temp rise + heavy load → tolerance excursion</li>
            </ul>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-mono text-slate-300 mb-1">
                Number of Batches
              </label>
              <input
                type="number"
                min={50}
                max={5000}
                step={50}
                value={nBatches}
                onChange={(e) => setNBatches(Number(e.target.value))}
                className="w-full bg-surface-900 border border-surface-600 rounded-lg px-3 py-2 text-xs font-mono text-slate-100 focus:outline-none focus:border-primary-500"
              />
            </div>
            <div>
              <label className="block text-xs font-mono text-slate-300 mb-1">
                Random Seed (Reproducibility)
              </label>
              <input
                type="number"
                value={randomSeed}
                onChange={(e) => setRandomSeed(Number(e.target.value))}
                className="w-full bg-surface-900 border border-surface-600 rounded-lg px-3 py-2 text-xs font-mono text-slate-100 focus:outline-none focus:border-primary-500"
              />
            </div>
          </div>

          <button
            onClick={() => generateMutation.mutate()}
            disabled={generateMutation.isPending}
            className="w-full btn-primary justify-center text-xs py-2.5"
          >
            {generateMutation.isPending ? (
              <>
                <RefreshCw className="w-4 h-4 animate-spin" />
                <span>Simulating Industrial Physics & Generating...</span>
              </>
            ) : (
              <>
                <Sparkles className="w-4 h-4" />
                <span>Generate & Ingest Benchmark Dataset</span>
              </>
            )}
          </button>
        </div>

        {/* Upload Custom Dataset Card */}
        <div className="card space-y-5 border-surface-600/80">
          <div className="flex items-center gap-3">
            <div className="p-2.5 rounded-lg bg-surface-700 text-slate-300 border border-surface-600">
              <UploadCloud className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-sm font-bold font-mono text-slate-100">
                Upload Custom Dataset
              </h2>
              <p className="text-xs text-slate-400">
                Supports CSV, JSON, or Parquet with automated schema validation and missingness audit
              </p>
            </div>
          </div>

          <div className="space-y-3">
            <div>
              <label className="block text-xs font-mono text-slate-300 mb-1">
                Dataset Name
              </label>
              <input
                type="text"
                placeholder="e.g. CNC Line 4 Telemetry 2024"
                value={uploadName}
                onChange={(e) => setUploadName(e.target.value)}
                className="w-full bg-surface-900 border border-surface-600 rounded-lg px-3 py-2 text-xs text-slate-100 focus:outline-none focus:border-primary-500"
              />
            </div>

            <div>
              <label className="block text-xs font-mono text-slate-300 mb-1">
                Description (Optional)
              </label>
              <input
                type="text"
                placeholder="Context on machine types, shifts, sensor types"
                value={uploadDesc}
                onChange={(e) => setUploadDesc(e.target.value)}
                className="w-full bg-surface-900 border border-surface-600 rounded-lg px-3 py-2 text-xs text-slate-100 focus:outline-none focus:border-primary-500"
              />
            </div>

            <div>
              <label className="block text-xs font-mono text-slate-300 mb-1">
                Select File (.csv, .json, .parquet)
              </label>
              <input
                type="file"
                accept=".csv,.json,.parquet"
                onChange={(e) => setUploadFile(e.target.files?.[0] || null)}
                className="w-full text-xs text-slate-400 file:mr-4 file:py-2 file:px-4 file:rounded-lg file:border-0 file:text-xs file:font-mono file:bg-surface-700 file:text-slate-200 hover:file:bg-surface-600 file:cursor-pointer"
              />
            </div>
          </div>

          <button
            onClick={() => uploadMutation.mutate()}
            disabled={!uploadFile || uploadMutation.isPending}
            className="w-full btn-secondary justify-center text-xs py-2.5 disabled:opacity-50"
          >
            {uploadMutation.isPending ? (
              <>
                <RefreshCw className="w-4 h-4 animate-spin" />
                <span>Validating & Uploading...</span>
              </>
            ) : (
              <>
                <UploadCloud className="w-4 h-4" />
                <span>Upload & Validate Dataset</span>
              </>
            )}
          </button>
        </div>
      </div>

      {/* Existing Datasets List */}
      <div className="card space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-base font-bold font-mono text-slate-100">
              Registered Industrial Datasets
            </h3>
            <p className="text-xs text-slate-400">
              Validated datasets available for failure investigations and benchmark evaluations
            </p>
          </div>
          <button
            onClick={() => queryClient.invalidateQueries({ queryKey: ['datasets'] })}
            className="p-1.5 rounded-lg bg-surface-700 hover:bg-surface-600 text-slate-400 transition-colors"
            title="Refresh"
          >
            <RefreshCw className="w-4 h-4" />
          </button>
        </div>

        {loadingDatasets ? (
          <LoadingState message="Loading registered datasets..." />
        ) : datasets?.length === 0 ? (
          <div className="p-8 text-center text-slate-400 text-xs">
            No datasets found. Use the generator or upload form above.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs font-mono">
              <thead className="bg-surface-900/60 text-slate-400 border-b border-surface-700">
                <tr>
                  <th className="p-3">Name</th>
                  <th className="p-3">Source Type</th>
                  <th className="p-3">Records</th>
                  <th className="p-3">Created</th>
                  <th className="p-3">Validation</th>
                  <th className="p-3">ID</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-surface-700/60">
                {datasets?.map((ds) => (
                  <tr key={ds.id} className="hover:bg-surface-700/30 transition-colors">
                    <td className="p-3 font-semibold text-slate-200">
                      <div>{ds.name}</div>
                      {ds.description && (
                        <div className="text-[11px] font-sans text-slate-400 font-normal line-clamp-1">
                          {ds.description}
                        </div>
                      )}
                    </td>
                    <td className="p-3">
                      <Badge variant={ds.source_type === 'synthetic' ? 'info' : 'primary'}>
                        {ds.source_type}
                      </Badge>
                    </td>
                    <td className="p-3 text-slate-300">{ds.record_count ?? 0}</td>
                    <td className="p-3 text-slate-400">
                      {new Date(ds.created_at).toLocaleDateString()}
                    </td>
                    <td className="p-3">
                      <span className="inline-flex items-center gap-1 text-accent-green">
                        <CheckCircle className="w-3.5 h-3.5" />
                        <span>Valid</span>
                      </span>
                    </td>
                    <td className="p-3 text-[10px] text-slate-500 font-mono select-all">
                      {ds.id}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  )
}

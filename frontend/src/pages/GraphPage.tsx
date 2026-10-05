import React, { useState, useMemo } from 'react'
import { useParams, Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import {
  GitFork,
  ArrowLeft,
  Filter,
  Layers,
  Info,
  Maximize2,
  RefreshCw,
  Search,
} from 'lucide-react'
import { api } from '../services/api'
import Badge from '../components/ui/Badge'
import { LoadingState, EmptyState } from '../components/ui/FeedbackStates'
import type { GraphNode, GraphLink } from '../types'

export default function GraphPage() {
  const { id } = useParams<{ id: string }>()
  const [selectedNode, setSelectedNode] = useState<GraphNode | null>(null)
  const [searchQuery, setSearchQuery] = useState('')
  const [activeFilter, setActiveFilter] = useState<string>('all')

  const { data: graphData, isLoading, refetch } = useQuery({
    queryKey: ['investigation-graph', id],
    queryFn: () => api.getInvestigationGraph(id!),
    enabled: !!id,
  })

  const nodeColorMap: Record<string, string> = {
    machine: '#3355ff',
    batch: '#06d6f0',
    material: '#06d690',
    sensor: '#f0d006',
    event: '#f03355',
    mechanism: '#b05cff',
  }

  const nodes = useMemo(() => graphData?.nodes || [], [graphData])
  const links = useMemo(() => graphData?.links || [], [graphData])

  const filteredNodes = useMemo(() => {
    return nodes.filter((n) => {
      const matchesFilter = activeFilter === 'all' || n.type === activeFilter
      const matchesSearch =
        !searchQuery ||
        n.label.toLowerCase().includes(searchQuery.toLowerCase()) ||
        n.id.toLowerCase().includes(searchQuery.toLowerCase())
      return matchesFilter && matchesSearch
    })
  }, [nodes, activeFilter, searchQuery])

  if (isLoading) return <LoadingState message="Synthesizing heterogeneous entity-event graph..." />

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
              Heterogeneous Relationship Graph
            </h1>
            <Badge variant="primary">{nodes.length} Nodes</Badge>
            <Badge variant="info">{links.length} Relations</Badge>
          </div>
          <p className="text-xs text-slate-400">
            Multi-relational graph connecting equipment, production batches, physical sensor channels, temporal events, and discovered failure mechanisms.
          </p>
        </div>

        <button
          onClick={() => refetch()}
          className="p-2 rounded-lg bg-surface-700 hover:bg-surface-600 text-slate-300 self-start sm:self-auto"
          title="Refresh Graph"
        >
          <RefreshCw className="w-4 h-4" />
        </button>
      </div>

      {/* Control / Filter Bar */}
      <div className="card p-3 flex flex-wrap items-center justify-between gap-4 bg-surface-800/90">
        <div className="flex flex-wrap items-center gap-2">
          <span className="text-xs font-mono text-slate-400 flex items-center gap-1 mr-1">
            <Filter className="w-3.5 h-3.5" />
            <span>Node Type:</span>
          </span>
          {['all', 'machine', 'batch', 'material', 'sensor', 'event', 'mechanism'].map((t) => (
            <button
              key={t}
              onClick={() => setActiveFilter(t)}
              className={`px-2.5 py-1 rounded-md text-xs font-mono capitalize transition-colors ${
                activeFilter === t
                  ? 'bg-primary-600 text-white font-semibold'
                  : 'bg-surface-700 text-slate-300 hover:bg-surface-600'
              }`}
            >
              {t}
            </button>
          ))}
        </div>

        <div className="relative min-w-[200px]">
          <Search className="w-3.5 h-3.5 text-slate-500 absolute left-3 top-2.5" />
          <input
            type="text"
            placeholder="Search nodes..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full bg-surface-900 border border-surface-600 rounded-lg pl-8 pr-3 py-1.5 text-xs text-slate-200 focus:outline-none focus:border-primary-500 font-mono"
          />
        </div>
      </div>

      {/* Main Graph Content */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Node Explorer & Network Canvas */}
        <div className="lg:col-span-2 card p-6 min-h-[500px] flex flex-col justify-between space-y-4 relative bg-surface-900/90">
          <div className="flex items-center justify-between">
            <div className="text-xs font-mono text-slate-400">
              Active Graph Topology ({filteredNodes.length} visible entities)
            </div>

            {/* Legend */}
            <div className="flex flex-wrap items-center gap-3 text-[11px] font-mono">
              {Object.entries(nodeColorMap).map(([type, color]) => (
                <div key={type} className="flex items-center gap-1">
                  <span
                    className="w-2.5 h-2.5 rounded-full"
                    style={{ backgroundColor: color }}
                  />
                  <span className="text-slate-400 capitalize">{type}</span>
                </div>
              ))}
            </div>
          </div>

          {/* Node Grid / Visual Cluster */}
          <div className="flex-1 p-4 rounded-xl bg-surface-800/40 border border-surface-700/60 flex flex-wrap gap-2.5 content-start overflow-y-auto max-h-[460px]">
            {filteredNodes.length === 0 ? (
              <div className="m-auto text-xs text-slate-500 font-mono">
                No nodes match the selected filter or query.
              </div>
            ) : (
              filteredNodes.map((n) => {
                const color = nodeColorMap[n.type] || '#64748b'
                const isSelected = selectedNode?.id === n.id
                return (
                  <button
                    key={n.id}
                    onClick={() => setSelectedNode(n)}
                    className={`px-3 py-2 rounded-lg text-xs font-mono border transition-all text-left flex items-center gap-2 ${
                      isSelected
                        ? 'border-accent-cyan bg-surface-700 shadow-glow-primary'
                        : 'border-surface-700 bg-surface-800/80 hover:border-surface-500 hover:bg-surface-700/60'
                    }`}
                  >
                    <span
                      className="w-2.5 h-2.5 rounded-full flex-shrink-0"
                      style={{ backgroundColor: color }}
                    />
                    <div className="truncate max-w-[140px]">
                      <div className="text-slate-200 font-medium">{n.label || n.id}</div>
                      <div className="text-[10px] text-slate-400 capitalize">{n.type}</div>
                    </div>
                  </button>
                )
              })
            )}
          </div>

          <div className="text-[11px] font-mono text-slate-500 flex items-center justify-between border-t border-surface-700/60 pt-3">
            <span>Click any entity node to inspect its local multi-hop dependencies.</span>
            <span>Heterogeneous NetworkX Graph Engine</span>
          </div>
        </div>

        {/* Selected Node Details & Connected Edges */}
        <div className="card p-5 space-y-4 bg-surface-800/90">
          <div className="flex items-center justify-between border-b border-surface-700 pb-3">
            <h3 className="text-sm font-bold font-mono text-slate-100">
              Entity Inspector
            </h3>
            {selectedNode && (
              <Badge variant="primary">{selectedNode.type}</Badge>
            )}
          </div>

          {selectedNode ? (
            <div className="space-y-4">
              <div>
                <span className="text-[10px] font-mono uppercase text-slate-500 block">
                  Identifier
                </span>
                <span className="text-xs font-mono font-bold text-accent-cyan break-all">
                  {selectedNode.id}
                </span>
              </div>

              <div>
                <span className="text-[10px] font-mono uppercase text-slate-500 block">
                  Label
                </span>
                <span className="text-sm font-medium text-slate-200">
                  {selectedNode.label}
                </span>
              </div>

              {selectedNode.properties && (
                <div>
                  <span className="text-[10px] font-mono uppercase text-slate-500 block mb-1.5">
                    Node Attributes
                  </span>
                  <div className="space-y-1 bg-surface-900/80 p-3 rounded-lg border border-surface-700 text-xs font-mono">
                    {Object.entries(selectedNode.properties).map(([k, v]) => (
                      <div key={k} className="flex justify-between gap-2">
                        <span className="text-slate-400">{k}:</span>
                        <span className="text-slate-200 font-semibold truncate max-w-[160px]">
                          {String(v)}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Connected relations */}
              <div>
                <span className="text-[10px] font-mono uppercase text-slate-500 block mb-1.5">
                  Connected Edges (Degree: {links.filter((l) => l.source === selectedNode.id || l.target === selectedNode.id).length})
                </span>
                <div className="space-y-2 max-h-56 overflow-y-auto pr-1">
                  {links
                    .filter((l) => l.source === selectedNode.id || l.target === selectedNode.id)
                    .map((l, i) => {
                      const isOutgoing = l.source === selectedNode.id
                      const otherId = isOutgoing ? l.target : l.source
                      return (
                        <div
                          key={i}
                          className="p-2 rounded bg-surface-900 border border-surface-700/80 text-[11px] font-mono space-y-1"
                        >
                          <div className="flex items-center justify-between text-slate-300">
                            <span className="text-accent-cyan font-semibold">
                              {l.relation}
                            </span>
                            <span className="text-[10px] text-slate-500">
                              {isOutgoing ? 'outgoing →' : '← incoming'}
                            </span>
                          </div>
                          <div className="text-slate-400 truncate">Target: {otherId}</div>
                        </div>
                      )
                    })}
                </div>
              </div>
            </div>
          ) : (
            <div className="p-8 text-center text-xs text-slate-500 font-mono">
              Select a node from the topology map to inspect its attributes, causal links, and dependency neighbors.
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

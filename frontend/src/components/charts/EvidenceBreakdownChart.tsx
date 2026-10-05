import React from 'react'
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  Legend,
  CartesianGrid,
  Cell,
} from 'recharts'
import type { CandidateMechanism } from '../../types'

interface EvidenceBreakdownChartProps {
  mechanism: CandidateMechanism
}

export default function EvidenceBreakdownChart({ mechanism }: EvidenceBreakdownChartProps) {
  const scoreData = [
    { name: 'Temporal Consistency', score: Math.round(mechanism.temporal_consistency_score * 100) },
    { name: 'Evidence Strength', score: Math.round(mechanism.evidence_strength_score * 100) },
    { name: 'Coverage', score: Math.round(mechanism.evidence_coverage_score * 100) },
    { name: 'Recurrence', score: Math.round(mechanism.recurrence_score * 100) },
    { name: 'Plausibility', score: Math.round(mechanism.plausibility_score * 100) },
    { name: 'Contradiction Penalty', score: -Math.round(mechanism.contradiction_penalty * 100) },
  ]

  const evidenceCounts = [
    { name: 'Supporting Evidence', count: mechanism.supporting_evidence_count, fill: '#06d690' },
    { name: 'Contradicting Evidence', count: mechanism.contradicting_evidence_count, fill: '#f03355' },
    { name: 'Missing Evidence', count: mechanism.missing_evidence_count, fill: '#f0d006' },
  ]

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
      {/* Scoring Breakdown */}
      <div className="card">
        <h4 className="text-sm font-semibold text-slate-200 font-mono mb-1">
          Mechanism Score Dimensions (%)
        </h4>
        <p className="text-xs text-slate-400 mb-4">
          Multi-factor objective scoring computed over temporal sensor & batch alignments
        </p>
        <div className="h-64">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart
              data={scoreData}
              layout="vertical"
              margin={{ top: 5, right: 30, left: 70, bottom: 5 }}
            >
              <CartesianGrid strokeDasharray="3 3" stroke="#243050" />
              <XAxis type="number" domain={[-100, 100]} stroke="#64748b" tick={{ fill: '#94a3b8', fontSize: 11 }} />
              <YAxis
                type="category"
                dataKey="name"
                stroke="#64748b"
                tick={{ fill: '#94a3b8', fontSize: 11 }}
                width={120}
              />
              <Tooltip
                contentStyle={{
                  backgroundColor: '#0f1225',
                  borderColor: '#243050',
                  borderRadius: '8px',
                  color: '#f8fafc',
                  fontSize: '12px',
                }}
                formatter={(val: number) => [`${val}%`, 'Score']}
              />
              <Bar dataKey="score" radius={[0, 4, 4, 0]}>
                {scoreData.map((entry, index) => (
                  <Cell
                    key={`cell-${index}`}
                    fill={entry.score >= 0 ? '#3355ff' : '#f03355'}
                  />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Evidence Polarity Counts */}
      <div className="card">
        <h4 className="text-sm font-semibold text-slate-200 font-mono mb-1">
          Evidence Item Distribution
        </h4>
        <p className="text-xs text-slate-400 mb-4">
          Counts of verified historical records supporting vs refuting the hypothesis
        </p>
        <div className="h-64">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart
              data={evidenceCounts}
              margin={{ top: 15, right: 30, left: 20, bottom: 5 }}
            >
              <CartesianGrid strokeDasharray="3 3" stroke="#243050" />
              <XAxis dataKey="name" stroke="#64748b" tick={{ fill: '#94a3b8', fontSize: 11 }} />
              <YAxis stroke="#64748b" tick={{ fill: '#94a3b8', fontSize: 11 }} />
              <Tooltip
                contentStyle={{
                  backgroundColor: '#0f1225',
                  borderColor: '#243050',
                  borderRadius: '8px',
                  color: '#f8fafc',
                  fontSize: '12px',
                }}
              />
              <Bar dataKey="count" radius={[4, 4, 0, 0]}>
                {evidenceCounts.map((entry, index) => (
                  <Cell key={`cell-ev-${index}`} fill={entry.fill} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  )
}

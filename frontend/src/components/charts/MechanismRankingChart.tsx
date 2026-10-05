import React from 'react'
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  Legend,
} from 'recharts'
import type { CandidateMechanism } from '../../types'

interface MechanismRankingChartProps {
  mechanisms: CandidateMechanism[]
  onSelectMechanism?: (mech: CandidateMechanism) => void
}

export default function MechanismRankingChart({
  mechanisms,
  onSelectMechanism,
}: MechanismRankingChartProps) {
  const chartData = mechanisms.slice(0, 7).map((m) => ({
    name: m.name.length > 22 ? m.name.substring(0, 20) + '...' : m.name,
    fullName: m.name,
    overallScore: Math.round(m.overall_score * 100),
    confidence: Math.round(m.confidence * 100),
    consistency: Math.round(m.temporal_consistency_score * 100),
    strength: Math.round(m.evidence_strength_score * 100),
    raw: m,
  }))

  return (
    <div className="card">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h4 className="text-sm font-semibold text-slate-200 font-mono">
            Candidate Mechanism Comparison
          </h4>
          <p className="text-xs text-slate-400">
            Ranked hypothesis breakdown across overall score, confidence, and temporal consistency
          </p>
        </div>
      </div>

      <div className="h-72">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={chartData} margin={{ top: 10, right: 30, left: 0, bottom: 25 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#243050" />
            <XAxis
              dataKey="name"
              stroke="#64748b"
              tick={{ fill: '#94a3b8', fontSize: 11 }}
              interval={0}
              angle={-15}
              textAnchor="end"
            />
            <YAxis
              stroke="#64748b"
              tick={{ fill: '#94a3b8', fontSize: 11 }}
              domain={[0, 100]}
              unit="%"
            />
            <Tooltip
              contentStyle={{
                backgroundColor: '#0f1225',
                borderColor: '#243050',
                borderRadius: '8px',
                color: '#f8fafc',
                fontSize: '12px',
              }}
              formatter={(val: number, name: string) => [`${val}%`, name]}
              labelFormatter={(label, payload) => {
                const item = payload?.[0]?.payload
                return item?.fullName || label
              }}
            />
            <Legend
              wrapperStyle={{ fontSize: '11px', paddingTop: '10px' }}
              iconType="circle"
            />
            <Bar dataKey="overallScore" name="Overall Score" fill="#3355ff" radius={[4, 4, 0, 0]} />
            <Bar dataKey="confidence" name="Confidence" fill="#06d6f0" radius={[4, 4, 0, 0]} />
            <Bar dataKey="consistency" name="Temporal Consistency" fill="#06d690" radius={[4, 4, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}

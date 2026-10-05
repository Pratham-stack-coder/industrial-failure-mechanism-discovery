import React from 'react'
import { LucideIcon } from 'lucide-react'

interface StatCardProps {
  title: string
  value: string | number
  subtitle?: string
  icon?: LucideIcon
  trend?: string
  trendType?: 'positive' | 'negative' | 'neutral'
  color?: 'primary' | 'cyan' | 'green' | 'orange' | 'red'
}

export default function StatCard({
  title,
  value,
  subtitle,
  icon: Icon,
  trend,
  trendType = 'neutral',
  color = 'primary',
}: StatCardProps) {
  const colorStyles = {
    primary: 'border-primary-500/30 text-primary-400 bg-primary-500/10',
    cyan: 'border-accent-cyan/30 text-accent-cyan bg-accent-cyan/10',
    green: 'border-accent-green/30 text-accent-green bg-accent-green/10',
    orange: 'border-accent-orange/30 text-accent-orange bg-accent-orange/10',
    red: 'border-accent-red/30 text-accent-red bg-accent-red/10',
  }

  return (
    <div className="card relative overflow-hidden group">
      <div className="flex items-start justify-between">
        <div>
          <p className="text-xs font-mono uppercase tracking-wider text-slate-400 font-medium">
            {title}
          </p>
          <div className="text-2xl font-bold font-mono mt-1 text-slate-100 group-hover:text-accent-cyan transition-colors">
            {value}
          </div>
          {subtitle && (
            <p className="text-xs text-slate-400 mt-1 font-sans">{subtitle}</p>
          )}
          {trend && (
            <div className="mt-2 flex items-center gap-1.5 text-xs font-mono">
              <span
                className={
                  trendType === 'positive'
                    ? 'text-accent-green'
                    : trendType === 'negative'
                    ? 'text-accent-red'
                    : 'text-slate-400'
                }
              >
                {trend}
              </span>
            </div>
          )}
        </div>

        {Icon && (
          <div className={`p-2.5 rounded-lg border ${colorStyles[color]} transition-transform group-hover:scale-110`}>
            <Icon className="w-5 h-5" />
          </div>
        )}
      </div>
      <div className="absolute inset-x-0 bottom-0 h-[2px] bg-gradient-to-r from-transparent via-primary-500/30 to-transparent opacity-0 group-hover:opacity-100 transition-opacity" />
    </div>
  )
}

import React from 'react'
import { Loader2 } from 'lucide-react'

interface LoadingStateProps {
  message?: string
  description?: string
}

export function LoadingState({
  message = 'Loading analysis data...',
  description = 'Processing heterogeneous temporal signals across datasets',
}: LoadingStateProps) {
  return (
    <div className="flex flex-col items-center justify-center p-12 text-center">
      <div className="relative">
        <Loader2 className="w-10 h-10 text-primary-500 animate-spin" />
        <div className="absolute inset-0 rounded-full blur-md bg-primary-500/20" />
      </div>
      <h3 className="text-base font-semibold text-slate-200 mt-4 font-mono">{message}</h3>
      {description && <p className="text-xs text-slate-400 mt-1 max-w-sm">{description}</p>}
    </div>
  )
}

interface EmptyStateProps {
  icon?: React.ReactNode
  title: string
  description: string
  action?: React.ReactNode
}

export function EmptyState({ icon, title, description, action }: EmptyStateProps) {
  return (
    <div className="card text-center p-10 flex flex-col items-center justify-center border-dashed border-surface-600/70">
      {icon && <div className="p-3 rounded-xl bg-surface-700/50 text-slate-400 mb-3">{icon}</div>}
      <h3 className="text-base font-semibold text-slate-200 font-mono">{title}</h3>
      <p className="text-xs text-slate-400 mt-1 max-w-md">{description}</p>
      {action && <div className="mt-5">{action}</div>}
    </div>
  )
}

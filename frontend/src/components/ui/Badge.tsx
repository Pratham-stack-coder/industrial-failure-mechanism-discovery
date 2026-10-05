import React from 'react'

export interface BadgeProps {
  children: React.ReactNode
  variant?: 'primary' | 'success' | 'warning' | 'danger' | 'info' | 'neutral'
  size?: 'sm' | 'md'
}

export default function Badge({ children, variant = 'neutral', size = 'sm' }: BadgeProps) {
  const variantStyles = {
    primary: 'bg-primary-950/80 text-primary-300 border-primary-800/80',
    success: 'bg-emerald-950/80 text-accent-green border-emerald-800/80',
    warning: 'bg-amber-950/80 text-accent-orange border-amber-800/80',
    danger: 'bg-rose-950/80 text-accent-red border-rose-800/80',
    info: 'bg-cyan-950/80 text-accent-cyan border-cyan-800/80',
    neutral: 'bg-surface-700/80 text-slate-300 border-surface-600',
  }

  const sizeStyles = {
    sm: 'text-[11px] px-2 py-0.5',
    md: 'text-xs px-2.5 py-1',
  }

  return (
    <span
      className={`inline-flex items-center font-mono font-medium rounded-full border ${variantStyles[variant]} ${sizeStyles[size]}`}
    >
      {children}
    </span>
  )
}

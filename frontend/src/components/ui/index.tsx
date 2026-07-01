import { type ReactNode } from 'react'
import { clsx } from 'clsx'
import { Loader2 } from 'lucide-react'

// ── Badge ─────────────────────────────────────────────────────────────────────

type BadgeVariant = 'green' | 'red' | 'yellow' | 'blue' | 'gray' | 'indigo'

const badgeStyles: Record<BadgeVariant, string> = {
  green:  'bg-emerald-50 text-emerald-700 ring-emerald-600/20',
  red:    'bg-red-50 text-red-700 ring-red-600/20',
  yellow: 'bg-amber-50 text-amber-700 ring-amber-600/20',
  blue:   'bg-blue-50 text-blue-700 ring-blue-600/20',
  gray:   'bg-gray-50 text-gray-600 ring-gray-500/20',
  indigo: 'bg-indigo-50 text-indigo-700 ring-indigo-600/20',
}

export function Badge({ children, variant = 'gray' }: { children: ReactNode; variant?: BadgeVariant }) {
  return (
    <span className={clsx(
      'inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ring-1 ring-inset',
      badgeStyles[variant],
    )}>
      {children}
    </span>
  )
}

// ── Card ──────────────────────────────────────────────────────────────────────

export function Card({ children, className }: { children: ReactNode; className?: string }) {
  return (
    <div className={clsx('bg-white rounded-xl border border-slate-200 shadow-sm', className)}>
      {children}
    </div>
  )
}

export function CardHeader({ title, subtitle, action }: { title: string; subtitle?: string; action?: ReactNode }) {
  return (
    <div className="flex items-start justify-between px-6 py-4 border-b border-slate-100">
      <div>
        <h3 className="text-sm font-semibold text-slate-900">{title}</h3>
        {subtitle && <p className="mt-0.5 text-xs text-slate-500">{subtitle}</p>}
      </div>
      {action && <div className="ml-4 flex-shrink-0">{action}</div>}
    </div>
  )
}

// ── Spinner ───────────────────────────────────────────────────────────────────

export function Spinner({ size = 'md', className }: { size?: 'sm' | 'md' | 'lg'; className?: string }) {
  const sizes = { sm: 'h-4 w-4', md: 'h-6 w-6', lg: 'h-8 w-8' }
  return <Loader2 className={clsx('animate-spin text-brand-500', sizes[size], className)} />
}

export function LoadingOverlay() {
  return (
    <div className="flex items-center justify-center py-16">
      <Spinner size="lg" />
    </div>
  )
}

// ── Status dot ────────────────────────────────────────────────────────────────

type StatusColor = 'green' | 'red' | 'yellow' | 'gray'
const dotColors: Record<StatusColor, string> = {
  green:  'bg-emerald-400',
  red:    'bg-red-400',
  yellow: 'bg-amber-400',
  gray:   'bg-gray-300',
}

export function StatusDot({ color, pulse }: { color: StatusColor; pulse?: boolean }) {
  return (
    <span className="relative flex h-2.5 w-2.5">
      {pulse && <span className={clsx('animate-ping absolute inline-flex h-full w-full rounded-full opacity-75', dotColors[color])} />}
      <span className={clsx('relative inline-flex rounded-full h-2.5 w-2.5', dotColors[color])} />
    </span>
  )
}

// ── Empty state ───────────────────────────────────────────────────────────────

export function EmptyState({ icon, title, description, action }: {
  icon?: ReactNode
  title: string
  description?: string
  action?: ReactNode
}) {
  return (
    <div className="flex flex-col items-center justify-center py-16 text-center">
      {icon && <div className="mb-4 text-slate-300">{icon}</div>}
      <p className="text-sm font-medium text-slate-700">{title}</p>
      {description && <p className="mt-1 text-xs text-slate-500 max-w-xs">{description}</p>}
      {action && <div className="mt-4">{action}</div>}
    </div>
  )
}

// ── Error banner ──────────────────────────────────────────────────────────────

export function ErrorBanner({ message }: { message: string }) {
  return (
    <div className="rounded-lg bg-red-50 border border-red-200 p-4">
      <p className="text-sm text-red-700">{message}</p>
    </div>
  )
}

// ── Button ────────────────────────────────────────────────────────────────────

type ButtonVariant = 'primary' | 'secondary' | 'danger' | 'ghost'

const btnStyles: Record<ButtonVariant, string> = {
  primary:   'bg-brand-600 text-white hover:bg-brand-700 focus-visible:ring-brand-500',
  secondary: 'bg-white text-slate-700 border border-slate-300 hover:bg-slate-50 focus-visible:ring-brand-500',
  danger:    'bg-red-600 text-white hover:bg-red-700 focus-visible:ring-red-500',
  ghost:     'text-slate-600 hover:bg-slate-100 focus-visible:ring-brand-500',
}

export function Button({
  children, variant = 'primary', size = 'md', disabled, isLoading, onClick, type = 'button', className,
}: {
  children: ReactNode
  variant?: ButtonVariant
  size?: 'sm' | 'md' | 'lg'
  disabled?: boolean
  isLoading?: boolean
  onClick?: () => void
  type?: 'button' | 'submit' | 'reset'
  className?: string
}) {
  const sizes = { sm: 'px-3 py-1.5 text-xs', md: 'px-4 py-2 text-sm', lg: 'px-6 py-3 text-base' }
  return (
    <button
      type={type}
      onClick={onClick}
      disabled={disabled || isLoading}
      className={clsx(
        'inline-flex items-center gap-2 font-medium rounded-lg transition-colors',
        'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-offset-2',
        'disabled:opacity-50 disabled:cursor-not-allowed',
        sizes[size], btnStyles[variant], className,
      )}
    >
      {isLoading && <Spinner size="sm" />}
      {children}
    </button>
  )
}

// ── Input ─────────────────────────────────────────────────────────────────────

export function Input({
  label, id, type = 'text', value, onChange, placeholder, error, required,
}: {
  label?: string
  id: string
  type?: string
  value: string
  onChange: (v: string) => void
  placeholder?: string
  error?: string
  required?: boolean
}) {
  return (
    <div>
      {label && (
        <label htmlFor={id} className="block text-sm font-medium text-slate-700 mb-1.5">
          {label}
        </label>
      )}
      <input
        id={id}
        type={type}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        required={required}
        className={clsx(
          'w-full rounded-lg border px-3 py-2 text-sm text-slate-900',
          'placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-transparent',
          error ? 'border-red-300 bg-red-50' : 'border-slate-300 bg-white',
        )}
      />
      {error && <p className="mt-1 text-xs text-red-600">{error}</p>}
    </div>
  )
}

// ── Select ────────────────────────────────────────────────────────────────────

export function Select({
  label, id, value, onChange, options, className,
}: {
  label?: string
  id: string
  value: string
  onChange: (v: string) => void
  options: { value: string; label: string }[]
  className?: string
}) {
  return (
    <div className={className}>
      {label && (
        <label htmlFor={id} className="block text-sm font-medium text-slate-700 mb-1.5">
          {label}
        </label>
      )}
      <select
        id={id}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 focus:outline-none focus:ring-2 focus:ring-brand-500"
      >
        {options.map((o) => (
          <option key={o.value} value={o.value}>{o.label}</option>
        ))}
      </select>
    </div>
  )
}

// ── Stat card ─────────────────────────────────────────────────────────────────

export function StatCard({ label, value, sub, accent }: {
  label: string
  value: string | number
  sub?: string
  accent?: string
}) {
  return (
    <Card className="p-5">
      <p className="text-xs font-medium text-slate-500 uppercase tracking-wider">{label}</p>
      <p className={clsx('mt-2 text-3xl font-bold tracking-tight', accent ?? 'text-slate-900')}>
        {value}
      </p>
      {sub && <p className="mt-1 text-xs text-slate-500">{sub}</p>}
    </Card>
  )
}

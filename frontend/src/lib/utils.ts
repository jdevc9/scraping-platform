import { clsx, type ClassValue } from 'clsx'

export function cn(...inputs: ClassValue[]) {
  return clsx(inputs)
}

export function formatCurrency(value: number | null | undefined, currency = 'BRL'): string {
  if (value == null) return '—'
  return new Intl.NumberFormat('pt-BR', {
    style: 'currency',
    currency,
    minimumFractionDigits: 2,
  }).format(value)
}

export function formatNumber(value: number | null | undefined): string {
  if (value == null) return '—'
  return new Intl.NumberFormat('pt-BR').format(value)
}

export function formatDate(iso: string | null | undefined): string {
  if (!iso) return '—'
  return new Intl.DateTimeFormat('pt-BR', {
    day: '2-digit', month: '2-digit', year: 'numeric',
    hour: '2-digit', minute: '2-digit',
  }).format(new Date(iso))
}

export function formatRelative(iso: string | null | undefined): string {
  if (!iso) return '—'
  const diff = Date.now() - new Date(iso).getTime()
  const mins = Math.floor(diff / 60_000)
  if (mins < 1)  return 'just now'
  if (mins < 60) return `${mins}m ago`
  const hrs = Math.floor(mins / 60)
  if (hrs < 24)  return `${hrs}h ago`
  return `${Math.floor(hrs / 24)}d ago`
}

export function pctChange(oldVal: number, newVal: number): number {
  if (oldVal === 0) return 0
  return ((newVal - oldVal) / oldVal) * 100
}

export const marketplaceLabel: Record<string, string> = {
  shopee: 'Shopee',
  jdcom:  'JD.com',
}

export const marketplaceBadge: Record<string, 'indigo' | 'blue'> = {
  shopee: 'indigo',
  jdcom:  'blue',
}

export function taskStatusColor(status: string): 'green' | 'yellow' | 'red' | 'gray' {
  switch (status) {
    case 'SUCCESS': return 'green'
    case 'STARTED':
    case 'PENDING': return 'yellow'
    case 'FAILURE': return 'red'
    default:        return 'gray'
  }
}

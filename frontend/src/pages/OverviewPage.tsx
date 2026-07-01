import { AlertTriangle, CheckCircle2, XCircle, Activity } from 'lucide-react'
import { useApi } from '@/hooks/useApi'
import { monitoringApi, productsApi, sellersApi } from '@/api'
import {
  Card, CardHeader, StatCard, StatusDot,
  LoadingOverlay, ErrorBanner, Badge,
} from '@/components/ui'
import { formatRelative, marketplaceLabel } from '@/lib/utils'

function HealthCard() {
  const { data, isLoading } = useApi(() => monitoringApi.health(), [], { pollInterval: 15_000 })

  if (isLoading && !data) return <Card className="p-5 animate-pulse h-36"><div /></Card>

  const isOk = data?.status === 'ok'
  return (
    <Card className="p-5">
      <div className="flex items-center justify-between mb-4">
        <p className="text-xs font-medium text-slate-500 uppercase tracking-wider">System Health</p>
        <StatusDot color={isOk ? 'green' : 'red'} pulse={isOk} />
      </div>
      <div className="flex items-center gap-2 mb-3">
        {isOk
          ? <CheckCircle2 className="h-5 w-5 text-emerald-500" />
          : <XCircle className="h-5 w-5 text-red-500" />}
        <span className={`text-lg font-bold ${isOk ? 'text-emerald-600' : 'text-red-600'}`}>
          {isOk ? 'All systems operational' : 'Degraded'}
        </span>
      </div>
      <div className="grid grid-cols-2 gap-2">
        {Object.entries(data?.services ?? {}).map(([svc, status]) => (
          <div key={svc} className="flex items-center gap-2 text-xs">
            <StatusDot color={status === 'ok' ? 'green' : 'red'} />
            <span className="text-slate-600 capitalize">{svc}</span>
          </div>
        ))}
      </div>
    </Card>
  )
}

function JobsCard() {
  const { data, isLoading } = useApi(() => monitoringApi.jobs(), [], { pollInterval: 10_000 })

  const activeCount   = Object.values(data?.active   ?? {}).flat().length
  const reservedCount = Object.values(data?.reserved ?? {}).flat().length

  if (isLoading && !data) return <Card className="p-5 animate-pulse h-36"><div /></Card>

  return (
    <Card className="p-5">
      <div className="flex items-center justify-between mb-4">
        <p className="text-xs font-medium text-slate-500 uppercase tracking-wider">Celery Workers</p>
        <Activity className="h-4 w-4 text-slate-400" />
      </div>
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <span className="text-sm text-slate-600">Active tasks</span>
          <Badge variant={activeCount > 0 ? 'indigo' : 'gray'}>{activeCount}</Badge>
        </div>
        <div className="flex items-center justify-between">
          <span className="text-sm text-slate-600">Queued</span>
          <Badge variant={reservedCount > 0 ? 'yellow' : 'gray'}>{reservedCount}</Badge>
        </div>
        <div className="flex items-center justify-between">
          <span className="text-sm text-slate-600">Workers online</span>
          <Badge variant="green">{Object.keys(data?.active ?? {}).length}</Badge>
        </div>
      </div>
      {data?.error && (
        <p className="mt-3 text-xs text-amber-600 bg-amber-50 rounded px-2 py-1">
          <AlertTriangle className="h-3 w-3 inline mr-1" />
          Broker unreachable
        </p>
      )}
    </Card>
  )
}

function RecentProductsTable() {
  const { data, isLoading, error } = useApi(
    () => productsApi.list({ page: 1, page_size: 8 }),
    [],
  )

  return (
    <Card>
      <CardHeader title="Recent Products" subtitle={`${data?.total ?? 0} tracked`} />
      {isLoading && !data ? <LoadingOverlay /> : error ? <ErrorBanner message={error} /> : (
        <div className="divide-y divide-slate-50">
          {data?.items.length === 0 ? (
            <p className="text-sm text-slate-400 text-center py-8">No products tracked yet.</p>
          ) : data?.items.map((p) => (
            <div key={p.id} className="flex items-center gap-3 px-5 py-3 hover:bg-slate-50 transition-colors">
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium text-slate-800 truncate">{p.title}</p>
                <p className="text-xs text-slate-400 mt-0.5">
                  {marketplaceLabel[p.marketplace]} · scraped {formatRelative(p.last_scraped_at)}
                </p>
              </div>
              <div className="text-right flex-shrink-0">
                <p className="text-sm font-semibold text-slate-900">
                  {p.price != null ? `R$ ${p.price.toFixed(2)}` : '—'}
                </p>
                <Badge variant={p.is_available ? 'green' : 'red'}>
                  {p.is_available ? 'In stock' : 'Out'}
                </Badge>
              </div>
            </div>
          ))}
        </div>
      )}
    </Card>
  )
}

export default function OverviewPage() {
  const { data: products } = useApi(() => productsApi.list({ page: 1, page_size: 1 }), [])
  const { data: sellers }  = useApi(() => sellersApi.list({ page: 1, page_size: 1 }), [])

  return (
    <div className="p-6 max-w-6xl mx-auto space-y-6 animate-fade-in">
      <div>
        <h1 className="text-xl font-bold text-slate-900">Overview</h1>
        <p className="text-sm text-slate-500 mt-0.5">Real-time marketplace intelligence</p>
      </div>

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard label="Products tracked" value={products?.total ?? '—'} accent="text-brand-700" />
        <StatCard label="Sellers monitored" value={sellers?.total ?? '—'} accent="text-emerald-700" />
        <HealthCard />
        <JobsCard />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <RecentProductsTable />
        <Card className="p-5">
          <CardHeader title="Quick Actions" subtitle="Trigger scraping jobs instantly" />
          <div className="p-5 space-y-3">
            {(['shopee', 'jdcom'] as const).map((mkt) => (
              <div key={mkt} className="flex items-center justify-between py-2 border-b border-slate-50 last:border-0">
                <div className="flex items-center gap-3">
                  <StatusDot color="green" pulse />
                  <span className="text-sm font-medium text-slate-700">{marketplaceLabel[mkt]}</span>
                </div>
                <a
                  href="/scraping"
                  className="text-xs font-medium text-brand-600 hover:text-brand-700 underline-offset-2 hover:underline"
                >
                  Trigger scrape →
                </a>
              </div>
            ))}
          </div>
        </Card>
      </div>
    </div>
  )
}

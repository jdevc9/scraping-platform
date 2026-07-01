import { useState } from 'react'
import { Store } from 'lucide-react'
import { useApi } from '@/hooks/useApi'
import { sellersApi, analyticsApi } from '@/api'
import {
  Card, CardHeader, Badge, Select, LoadingOverlay, ErrorBanner, EmptyState,
} from '@/components/ui'
import {
  ResponsiveContainer, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Cell,
} from 'recharts'
import { formatNumber, marketplaceLabel, marketplaceBadge } from '@/lib/utils'

function ScoreBar({ score }: { score: number | null }) {
  if (score == null) return <span className="text-xs text-slate-400">—</span>
  const pct = (score / 5) * 100
  const color = score >= 4.5 ? 'bg-emerald-400' : score >= 3.5 ? 'bg-amber-400' : 'bg-red-400'
  return (
    <div className="flex items-center gap-2">
      <div className="h-1.5 w-20 bg-slate-100 rounded-full overflow-hidden">
        <div className={`h-full ${color} rounded-full transition-all`} style={{ width: `${pct}%` }} />
      </div>
      <span className="text-xs font-medium text-slate-700 tabular-nums">{score.toFixed(1)}</span>
    </div>
  )
}

function SellerAnalyticsChart({ marketplace }: { marketplace: string }) {
  const { data, isLoading } = useApi(
    () => analyticsApi.sellers({ marketplace: marketplace || undefined, limit: 10 }),
    [marketplace],
  )

  const chartData = (data?.sellers ?? []).map((s) => ({
    name: s.name.length > 14 ? s.name.slice(0, 13) + '…' : s.name,
    tracked: s.tracked_products,
    score: s.score ?? 0,
  }))

  return (
    <Card>
      <CardHeader title="Top Sellers by Tracked Products" subtitle="Products you're monitoring per seller" />
      <div className="p-5">
        {isLoading ? (
          <LoadingOverlay />
        ) : chartData.length === 0 ? (
          <EmptyState title="No seller data" description="Add products to see seller analytics." />
        ) : (
          <ResponsiveContainer width="100%" height={200}>
            <BarChart data={chartData} margin={{ top: 4, right: 4, left: 0, bottom: 28 }}>
              <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
              <XAxis
                dataKey="name"
                tick={{ fontSize: 10, fill: '#94a3b8' }}
                axisLine={false}
                tickLine={false}
                angle={-30}
                textAnchor="end"
              />
              <YAxis
                tick={{ fontSize: 10, fill: '#94a3b8' }}
                axisLine={false}
                tickLine={false}
                allowDecimals={false}
              />
              <Tooltip
                contentStyle={{ fontSize: 12, borderRadius: 8, border: '1px solid #e2e8f0' }}
                formatter={(v: number) => [v, 'Products']}
              />
              <Bar dataKey="tracked" radius={[4, 4, 0, 0]} maxBarSize={36}>
                {chartData.map((_, i) => (
                  <Cell key={i} fill={i % 2 === 0 ? '#6366f1' : '#818cf8'} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        )}
      </div>
    </Card>
  )
}

export default function SellersPage() {
  const [page, setPage] = useState(1)
  const [marketplace, setMarketplace] = useState('')

  const { data, isLoading, error } = useApi(
    () => sellersApi.list({ page, page_size: 20, marketplace: marketplace || undefined }),
    [page, marketplace],
  )

  return (
    <div className="p-6 max-w-6xl mx-auto space-y-5 animate-fade-in">
      <div>
        <h1 className="text-xl font-bold text-slate-900">Sellers</h1>
        <p className="text-sm text-slate-500 mt-0.5">{data?.total ?? 0} sellers monitored</p>
      </div>

      <SellerAnalyticsChart marketplace={marketplace} />

      {/* Filter */}
      <div className="flex items-center gap-3">
        <Select
          id="sellers-mkt"
          value={marketplace}
          onChange={(v) => { setMarketplace(v); setPage(1) }}
          options={[
            { value: '', label: 'All marketplaces' },
            { value: 'shopee', label: 'Shopee' },
            { value: 'jdcom', label: 'JD.com' },
          ]}
          className="w-44"
        />
      </div>

      {/* Table */}
      <Card>
        {error ? <ErrorBanner message={error} /> : isLoading && !data ? <LoadingOverlay /> : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-slate-100 text-left">
                  {['Seller', 'Marketplace', 'Score', 'Products (total)', 'Status'].map((h) => (
                    <th key={h} className="px-5 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wider whitespace-nowrap">
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-50">
                {data?.items.length === 0 ? (
                  <tr><td colSpan={5}>
                    <EmptyState
                      icon={<Store className="h-8 w-8" />}
                      title="No sellers yet"
                      description="Sellers appear automatically when products are scraped."
                    />
                  </td></tr>
                ) : data?.items.map((s) => (
                  <tr key={s.id} className="hover:bg-slate-50 transition-colors">
                    <td className="px-5 py-3.5">
                      <p className="font-medium text-slate-800">{s.name}</p>
                      <p className="text-xs text-slate-400 mt-0.5 font-mono">{s.external_id}</p>
                    </td>
                    <td className="px-5 py-3.5">
                      <Badge variant={marketplaceBadge[s.marketplace] ?? 'gray'}>
                        {marketplaceLabel[s.marketplace]}
                      </Badge>
                    </td>
                    <td className="px-5 py-3.5">
                      <ScoreBar score={s.score} />
                    </td>
                    <td className="px-5 py-3.5 text-slate-600 tabular-nums">
                      {formatNumber(s.total_products)}
                    </td>
                    <td className="px-5 py-3.5">
                      <Badge variant={s.is_active ? 'green' : 'gray'}>
                        {s.is_active ? 'Active' : 'Inactive'}
                      </Badge>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>
    </div>
  )
}

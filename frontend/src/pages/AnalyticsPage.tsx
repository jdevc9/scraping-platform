import { useState } from 'react'
import { TrendingDown, TrendingUp, Minus } from 'lucide-react'
import { useApi } from '@/hooks/useApi'
import { productsApi, analyticsApi } from '@/api'
import {
  Card, CardHeader, StatCard, Select, LoadingOverlay, ErrorBanner, EmptyState,
} from '@/components/ui'
import { PriceTrendChart } from '@/components/charts/PriceTrendChart'
import { formatCurrency } from '@/lib/utils'

export default function AnalyticsPage() {
  const [selectedProductId, setSelectedProductId] = useState('')
  const [days, setDays] = useState('30')

  const { data: products } = useApi(
    () => productsApi.list({ page: 1, page_size: 100 }),
    [],
  )

  const { data: analytics, isLoading, error } = useApi(
    () => selectedProductId
      ? analyticsApi.prices(selectedProductId, Number(days))
      : Promise.resolve(null),
    [selectedProductId, days],
  )

  const productOptions = [
    { value: '', label: 'Select a product…' },
    ...(products?.items ?? []).map((p) => ({
      value: p.id,
      label: p.title.length > 55 ? p.title.slice(0, 54) + '…' : p.title,
    })),
  ]

  const priceChange = analytics && analytics.current_price && analytics.avg_price
    ? analytics.current_price - analytics.avg_price
    : null
  const priceTrend = priceChange == null ? null : priceChange < -0.5 ? 'down' : priceChange > 0.5 ? 'up' : 'flat'

  return (
    <div className="p-6 max-w-5xl mx-auto space-y-5 animate-fade-in">
      <div>
        <h1 className="text-xl font-bold text-slate-900">Analytics</h1>
        <p className="text-sm text-slate-500 mt-0.5">Price history and trend explorer</p>
      </div>

      {/* Controls */}
      <div className="flex flex-wrap gap-3 items-end">
        <Select
          id="product-select"
          label="Product"
          value={selectedProductId}
          onChange={setSelectedProductId}
          options={productOptions}
          className="flex-1 min-w-64"
        />
        <Select
          id="days-select"
          label="Period"
          value={days}
          onChange={setDays}
          options={[
            { value: '7',   label: 'Last 7 days' },
            { value: '14',  label: 'Last 14 days' },
            { value: '30',  label: 'Last 30 days' },
            { value: '90',  label: 'Last 90 days' },
          ]}
          className="w-44"
        />
      </div>

      {!selectedProductId ? (
        <Card>
          <EmptyState
            icon={<TrendingDown className="h-8 w-8" />}
            title="Select a product to view its price history"
            description="Choose from the dropdown above to explore price trends, highs, lows, and changes."
          />
        </Card>
      ) : error ? (
        <ErrorBanner message={error} />
      ) : isLoading ? (
        <LoadingOverlay />
      ) : analytics ? (
        <>
          {/* Stat row */}
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
            <StatCard label="Current price" value={formatCurrency(analytics.current_price)} accent="text-brand-700" />
            <StatCard label="Min price" value={formatCurrency(analytics.min_price)} accent="text-emerald-700" />
            <StatCard label="Max price" value={formatCurrency(analytics.max_price)} accent="text-red-700" />
            <StatCard label="Avg price" value={formatCurrency(analytics.avg_price)} />
          </div>

          {/* Trend indicator */}
          {priceTrend && (
            <div className={`flex items-center gap-2 px-4 py-2.5 rounded-lg text-sm font-medium w-fit ${
              priceTrend === 'down' ? 'bg-emerald-50 text-emerald-700 border border-emerald-200' :
              priceTrend === 'up'   ? 'bg-red-50 text-red-700 border border-red-200' :
                                      'bg-slate-50 text-slate-600 border border-slate-200'
            }`}>
              {priceTrend === 'down' ? <TrendingDown className="h-4 w-4" /> :
               priceTrend === 'up'   ? <TrendingUp   className="h-4 w-4" /> :
                                       <Minus         className="h-4 w-4" />}
              Price is {priceTrend === 'flat' ? 'stable' : priceTrend === 'down' ? 'trending down' : 'trending up'} vs average
              {priceChange != null && ` (${priceChange > 0 ? '+' : ''}${formatCurrency(priceChange)})`}
            </div>
          )}

          {/* Chart */}
          <Card>
            <CardHeader
              title="Price over time"
              subtitle={`${analytics.data_points} data points · ${days} days`}
            />
            <div className="px-4 py-4">
              {analytics.history.length === 0 ? (
                <EmptyState
                  title="No price history for this period"
                  description="Schedule a scrape to start collecting price data."
                />
              ) : (
                <PriceTrendChart
                  data={analytics.history}
                  avgPrice={analytics.avg_price}
                  minPrice={analytics.min_price}
                />
              )}
            </div>
          </Card>

          {/* Change log */}
          {analytics.history.filter((p) => p.price_changed).length > 0 && (
            <Card>
              <CardHeader title="Price changes detected" subtitle="Only scrapes where price changed are shown" />
              <div className="divide-y divide-slate-50">
                {analytics.history
                  .filter((p) => p.price_changed)
                  .slice(-10)
                  .reverse()
                  .map((p, i) => (
                    <div key={i} className="flex items-center justify-between px-5 py-3">
                      <p className="text-sm text-slate-600">{new Date(p.scraped_at).toLocaleString('pt-BR')}</p>
                      <div className="flex items-center gap-3">
                        <span className="text-sm font-semibold text-slate-900">{formatCurrency(p.price)}</span>
                        {p.price_diff != null && (
                          <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${
                            p.price_diff < 0 ? 'bg-emerald-50 text-emerald-700' : 'bg-red-50 text-red-700'
                          }`}>
                            {p.price_diff > 0 ? '+' : ''}{formatCurrency(p.price_diff)}
                          </span>
                        )}
                      </div>
                    </div>
                  ))}
              </div>
            </Card>
          )}
        </>
      ) : null}
    </div>
  )
}

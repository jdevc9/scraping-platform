import { useState, useCallback } from 'react'
import { Search, ExternalLink, RefreshCw, ChevronLeft, ChevronRight } from 'lucide-react'
import { useApi } from '@/hooks/useApi'
import { productsApi, analyticsApi, scrapingApi } from '@/api'
import {
  Card, Badge, Button, Select,
  LoadingOverlay, ErrorBanner, EmptyState, Spinner,
} from '@/components/ui'
import { PriceTrendChart } from '@/components/charts/PriceTrendChart'
import { formatCurrency, formatRelative, marketplaceLabel, marketplaceBadge } from '@/lib/utils'
import type { Product } from '@/types'

// ── Product detail drawer ─────────────────────────────────────────────────────

function ProductDrawer({ product, onClose }: { product: Product; onClose: () => void }) {
  const { data: analytics, isLoading } = useApi(
    () => analyticsApi.prices(product.id, 30),
    [product.id],
  )
  const [triggering, setTriggering] = useState(false)
  const [taskId, setTaskId] = useState<string | null>(null)

  async function handleScrape() {
    setTriggering(true)
    try {
      const res = await scrapingApi.triggerProduct(product.id)
      setTaskId(res.task_id)
    } catch {
      // silent
    } finally {
      setTriggering(false)
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex">
      {/* backdrop */}
      <div className="flex-1 bg-black/30 backdrop-blur-sm" onClick={onClose} />

      {/* panel */}
      <div className="w-full max-w-md bg-white shadow-2xl flex flex-col animate-slide-up overflow-y-auto">
        <div className="flex items-start justify-between p-5 border-b border-slate-100">
          <div className="flex-1 min-w-0 pr-4">
            <p className="text-xs text-slate-400 mb-1">{marketplaceLabel[product.marketplace]}</p>
            <h2 className="text-sm font-semibold text-slate-900 leading-snug line-clamp-2">{product.title}</h2>
          </div>
          <button onClick={onClose} className="text-slate-400 hover:text-slate-700 transition-colors text-lg leading-none">✕</button>
        </div>

        <div className="p-5 space-y-5 flex-1">
          {/* Price */}
          <div className="flex items-end gap-3">
            <div>
              <p className="text-xs text-slate-400 mb-0.5">Current price</p>
              <p className="text-3xl font-bold text-slate-900">{formatCurrency(product.price)}</p>
            </div>
            {product.original_price && product.original_price > (product.price ?? 0) && (
              <p className="text-sm text-slate-400 line-through mb-1">{formatCurrency(product.original_price)}</p>
            )}
            <div className="ml-auto">
              <Badge variant={product.is_available ? 'green' : 'red'}>
                {product.is_available ? 'In stock' : 'Out of stock'}
              </Badge>
            </div>
          </div>

          {/* Price chart */}
          <div>
            <p className="text-xs font-medium text-slate-500 mb-2">Price trend (30 days)</p>
            {isLoading ? (
              <div className="flex justify-center py-10"><Spinner /></div>
            ) : analytics && analytics.history.length > 0 ? (
              <PriceTrendChart
                data={analytics.history}
                avgPrice={analytics.avg_price}
                minPrice={analytics.min_price}
              />
            ) : (
              <p className="text-xs text-slate-400 text-center py-8">No price history yet.</p>
            )}
          </div>

          {/* Stats row */}
          {analytics && (
            <div className="grid grid-cols-3 gap-3 text-center">
              {[
                { label: 'Min', value: formatCurrency(analytics.min_price) },
                { label: 'Avg', value: formatCurrency(analytics.avg_price) },
                { label: 'Max', value: formatCurrency(analytics.max_price) },
              ].map(({ label, value }) => (
                <div key={label} className="bg-slate-50 rounded-lg py-3">
                  <p className="text-xs text-slate-400">{label}</p>
                  <p className="text-sm font-semibold text-slate-800 mt-0.5">{value}</p>
                </div>
              ))}
            </div>
          )}

          {/* Meta */}
          <div className="space-y-2 text-sm">
            {[
              { label: 'SKU', value: product.sku ?? '—' },
              { label: 'Stock', value: product.stock_quantity ?? '—' },
              { label: 'Rating', value: product.rating ? `${product.rating} ★ (${product.reviews_count})` : '—' },
              { label: 'Last scraped', value: formatRelative(product.last_scraped_at) },
            ].map(({ label, value }) => (
              <div key={label} className="flex justify-between">
                <span className="text-slate-400">{label}</span>
                <span className="text-slate-700 font-medium">{value}</span>
              </div>
            ))}
          </div>
        </div>

        {/* Footer */}
        <div className="p-5 border-t border-slate-100 flex items-center gap-3">
          <Button
            variant="secondary"
            size="sm"
            onClick={handleScrape}
            isLoading={triggering}
            className="flex-1 justify-center"
          >
            <RefreshCw className="h-3.5 w-3.5" />
            Scrape now
          </Button>
          {product.url && (
            <a
              href={product.url}
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center gap-1.5 text-xs font-medium text-brand-600 hover:text-brand-700"
            >
              <ExternalLink className="h-3.5 w-3.5" />
              View listing
            </a>
          )}
        </div>

        {taskId && (
          <p className="px-5 pb-4 text-xs text-emerald-600 font-mono bg-emerald-50">
            ✓ Task queued: {taskId}
          </p>
        )}
      </div>
    </div>
  )
}

// ── Main page ─────────────────────────────────────────────────────────────────

export default function ProductsPage() {
  const [page, setPage] = useState(1)
  const [search, setSearch] = useState('')
  const [marketplace, setMarketplace] = useState('')
  const [availability, setAvailability] = useState('')
  const [selected, setSelected] = useState<Product | null>(null)

  const { data, isLoading, error, refetch } = useApi(
    () => productsApi.list({
      page,
      page_size: 20,
      search: search || undefined,
      marketplace: marketplace || undefined,
      is_available: availability === '' ? undefined : availability === 'true',
    }),
    [page, search, marketplace, availability],
  )

  const handleSearch = useCallback((v: string) => {
    setSearch(v)
    setPage(1)
  }, [])

  return (
    <div className="p-6 max-w-6xl mx-auto space-y-5 animate-fade-in">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-slate-900">Products</h1>
          <p className="text-sm text-slate-500 mt-0.5">{data?.total ?? 0} products tracked</p>
        </div>
        <Button variant="secondary" size="sm" onClick={refetch}>
          <RefreshCw className="h-3.5 w-3.5" />
          Refresh
        </Button>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap gap-3">
        <div className="relative flex-1 min-w-48">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400" />
          <input
            type="text"
            value={search}
            onChange={(e) => handleSearch(e.target.value)}
            placeholder="Search products…"
            className="w-full pl-9 pr-3 py-2 text-sm border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-brand-500"
          />
        </div>
        <Select
          id="mkt-filter"
          value={marketplace}
          onChange={(v) => { setMarketplace(v); setPage(1) }}
          options={[
            { value: '', label: 'All marketplaces' },
            { value: 'shopee', label: 'Shopee' },
            { value: 'jdcom', label: 'JD.com' },
          ]}
          className="w-44"
        />
        <Select
          id="avail-filter"
          value={availability}
          onChange={(v) => { setAvailability(v); setPage(1) }}
          options={[
            { value: '', label: 'All availability' },
            { value: 'true', label: 'In stock' },
            { value: 'false', label: 'Out of stock' },
          ]}
          className="w-40"
        />
      </div>

      {/* Table */}
      <Card>
        {error ? <ErrorBanner message={error} /> : isLoading && !data ? <LoadingOverlay /> : (
          <>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-slate-100 text-left">
                    {['Product', 'Marketplace', 'Price', 'Stock', 'Rating', 'Last scraped'].map((h) => (
                      <th key={h} className="px-5 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wider whitespace-nowrap">
                        {h}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-50">
                  {data?.items.length === 0 ? (
                    <tr><td colSpan={6}>
                      <EmptyState title="No products found" description="Try adjusting your search or filters." />
                    </td></tr>
                  ) : data?.items.map((p) => (
                    <tr
                      key={p.id}
                      onClick={() => setSelected(p)}
                      className="hover:bg-slate-50 cursor-pointer transition-colors group"
                    >
                      <td className="px-5 py-3.5">
                        <p className="font-medium text-slate-800 group-hover:text-brand-700 transition-colors line-clamp-1 max-w-xs">
                          {p.title}
                        </p>
                        <p className="text-xs text-slate-400 mt-0.5 font-mono">{p.external_id}</p>
                      </td>
                      <td className="px-5 py-3.5">
                        <Badge variant={marketplaceBadge[p.marketplace] ?? 'gray'}>
                          {marketplaceLabel[p.marketplace]}
                        </Badge>
                      </td>
                      <td className="px-5 py-3.5">
                        <p className="font-semibold text-slate-900">{formatCurrency(p.price)}</p>
                        {p.original_price && p.original_price > (p.price ?? 0) && (
                          <p className="text-xs text-slate-400 line-through">{formatCurrency(p.original_price)}</p>
                        )}
                      </td>
                      <td className="px-5 py-3.5">
                        <Badge variant={p.is_available ? 'green' : 'red'}>
                          {p.is_available ? (p.stock_quantity != null ? p.stock_quantity : 'In stock') : 'Out'}
                        </Badge>
                      </td>
                      <td className="px-5 py-3.5 text-slate-600">
                        {p.rating ? `${p.rating} ★` : '—'}
                      </td>
                      <td className="px-5 py-3.5 text-slate-400 text-xs whitespace-nowrap">
                        {formatRelative(p.last_scraped_at)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {/* Pagination */}
            {data && data.pages > 1 && (
              <div className="flex items-center justify-between px-5 py-3 border-t border-slate-100">
                <p className="text-xs text-slate-500">
                  Page {data.page} of {data.pages} · {data.total} total
                </p>
                <div className="flex gap-1">
                  <button
                    onClick={() => setPage(p => Math.max(1, p - 1))}
                    disabled={page === 1}
                    className="p-1.5 rounded text-slate-400 hover:text-slate-700 hover:bg-slate-100 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
                  >
                    <ChevronLeft className="h-4 w-4" />
                  </button>
                  <button
                    onClick={() => setPage(p => Math.min(data.pages, p + 1))}
                    disabled={page === data.pages}
                    className="p-1.5 rounded text-slate-400 hover:text-slate-700 hover:bg-slate-100 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
                  >
                    <ChevronRight className="h-4 w-4" />
                  </button>
                </div>
              </div>
            )}
          </>
        )}
      </Card>

      {selected && (
        <ProductDrawer product={selected} onClose={() => setSelected(null)} />
      )}
    </div>
  )
}

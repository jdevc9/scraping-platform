import { useState } from 'react'
import { Play, Search as SearchIcon, CheckCircle2, XCircle, Clock, Loader2 } from 'lucide-react'
import { scrapingApi } from '@/api'
import { Card, CardHeader, Button, Input, Select, Badge } from '@/components/ui'
import { useApi } from '@/hooks/useApi'
import type { TaskStatus } from '@/types'

// ── Task status badge ─────────────────────────────────────────────────────────

function TaskStatusBadge({ status }: { status: string }) {
  const icon = {
    SUCCESS: <CheckCircle2 className="h-3.5 w-3.5" />,
    FAILURE: <XCircle     className="h-3.5 w-3.5" />,
    STARTED: <Loader2     className="h-3.5 w-3.5 animate-spin" />,
    PENDING: <Clock       className="h-3.5 w-3.5" />,
  }[status] ?? <Clock className="h-3.5 w-3.5" />

  const badgeVariant: Record<string, 'green' | 'red' | 'yellow' | 'gray'> = {
    SUCCESS: 'green', FAILURE: 'red', STARTED: 'yellow', PENDING: 'gray',
  }

  return (
    <Badge variant={badgeVariant[status] ?? 'gray'}>
      <span className="flex items-center gap-1">{icon}{status}</span>
    </Badge>
  )
}

// ── Task tracker — polls until terminal state ─────────────────────────────────

function TaskTracker({ taskId }: { taskId: string }) {
  // Poll every 3s; once terminal status reached, interval stays but result is cached
  const { data } = useApi<TaskStatus>(
    () => scrapingApi.taskStatus(taskId),
    [taskId],
    { pollInterval: 3_000 },
  )

  const isTerminal = data?.status === 'SUCCESS' || data?.status === 'FAILURE'

  return (
    <div className="flex items-center justify-between bg-slate-50 rounded-lg px-4 py-3 text-sm font-mono">
      <span className="text-slate-500 text-xs truncate max-w-xs">{taskId}</span>
      {data
        ? <TaskStatusBadge status={data.status} />
        : <Badge variant="gray">Polling…</Badge>
      }
      {isTerminal && (
        <span className="sr-only">Done</span>
      )}
    </div>
  )
}

// ── Trigger marketplace card ──────────────────────────────────────────────────

function TriggerCard() {
  const [marketplace, setMarketplace] = useState('shopee')
  const [loading, setLoading] = useState(false)
  const [taskIds, setTaskIds] = useState<string[]>([])

  async function handleTrigger() {
    setLoading(true)
    try {
      const res = await scrapingApi.triggerMarketplace(marketplace)
      setTaskIds((prev) => [res.task_id, ...prev].slice(0, 5))
    } catch {
      // silent — API errors show in the task row
    } finally {
      setLoading(false)
    }
  }

  return (
    <Card>
      <CardHeader title="Trigger Marketplace Scrape" subtitle="Fan-out: scrapes all tracked products for the selected marketplace" />
      <div className="p-5 space-y-4">
        <Select
          id="trigger-mkt"
          label="Marketplace"
          value={marketplace}
          onChange={setMarketplace}
          options={[
            { value: 'shopee', label: 'Shopee' },
            { value: 'jdcom', label: 'JD.com' },
          ]}
        />
        <Button onClick={handleTrigger} isLoading={loading} className="w-full justify-center">
          <Play className="h-4 w-4" />
          Trigger scrape
        </Button>
        {taskIds.length > 0 && (
          <div className="space-y-2">
            <p className="text-xs text-slate-400 font-medium">Recent tasks</p>
            {taskIds.map((id) => <TaskTracker key={id} taskId={id} />)}
          </div>
        )}
      </div>
    </Card>
  )
}

// ── Search & discover card ────────────────────────────────────────────────────

function SearchCard() {
  const [marketplace, setMarketplace] = useState('shopee')
  const [keyword, setKeyword] = useState('')
  const [maxResults, setMaxResults] = useState('20')
  const [loading, setLoading] = useState(false)
  const [taskIds, setTaskIds] = useState<string[]>([])
  const [error, setError] = useState('')

  async function handleSearch() {
    if (!keyword.trim()) { setError('Enter a keyword'); return }
    setError('')
    setLoading(true)
    try {
      const res = await scrapingApi.search(marketplace, keyword.trim(), Number(maxResults))
      setTaskIds((prev) => [res.task_id, ...prev].slice(0, 5))
      setKeyword('')
    } catch {
      setError('Failed to queue search task')
    } finally {
      setLoading(false)
    }
  }

  return (
    <Card>
      <CardHeader title="Search & Track Products" subtitle="Discover products by keyword and add them to monitoring" />
      <div className="p-5 space-y-4">
        <Select
          id="search-mkt"
          label="Marketplace"
          value={marketplace}
          onChange={setMarketplace}
          options={[
            { value: 'shopee', label: 'Shopee' },
            { value: 'jdcom', label: 'JD.com' },
          ]}
        />
        <Input
          id="keyword"
          label="Keyword"
          value={keyword}
          onChange={setKeyword}
          placeholder="e.g. iphone 15, xiaomi, airpods"
          error={error}
        />
        <Select
          id="max-results"
          label="Max products to discover"
          value={maxResults}
          onChange={setMaxResults}
          options={[
            { value: '10', label: '10 products' },
            { value: '20', label: '20 products' },
            { value: '50', label: '50 products' },
          ]}
        />
        <Button onClick={handleSearch} isLoading={loading} className="w-full justify-center">
          <SearchIcon className="h-4 w-4" />
          Search & track
        </Button>
        {taskIds.length > 0 && (
          <div className="space-y-2">
            <p className="text-xs text-slate-400 font-medium">Search tasks</p>
            {taskIds.map((id) => <TaskTracker key={id} taskId={id} />)}
          </div>
        )}
      </div>
    </Card>
  )
}

// ── Main page ─────────────────────────────────────────────────────────────────

export default function ScrapingPage() {
  return (
    <div className="p-6 max-w-4xl mx-auto space-y-5 animate-fade-in">
      <div>
        <h1 className="text-xl font-bold text-slate-900">Scraping Control</h1>
        <p className="text-sm text-slate-500 mt-0.5">Trigger scraping jobs and discover new products</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <TriggerCard />
        <SearchCard />
      </div>

      <Card className="p-5">
        <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-3">How scraping works</p>
        <div className="grid grid-cols-3 gap-4 text-xs text-slate-600">
          {[
            { step: '1', label: 'Trigger', desc: 'You queue a task via this UI or Celery Beat runs it automatically on schedule.' },
            { step: '2', label: 'Scrape', desc: 'Playwright or Selenium fetches product data using proxy rotation and stealth mode.' },
            { step: '3', label: 'Alert', desc: 'If price or stock changed, an alert is fired to the configured webhook.' },
          ].map(({ step, label, desc }) => (
            <div key={step} className="flex gap-3">
              <span className="flex-shrink-0 h-5 w-5 rounded-full bg-brand-100 text-brand-700 text-xs font-bold flex items-center justify-center">
                {step}
              </span>
              <div>
                <p className="font-semibold text-slate-700 mb-0.5">{label}</p>
                <p>{desc}</p>
              </div>
            </div>
          ))}
        </div>
      </Card>
    </div>
  )
}

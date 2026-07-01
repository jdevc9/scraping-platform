import { Activity, Clock, CheckCircle2, XCircle, RotateCcw } from 'lucide-react'
import { useApi } from '@/hooks/useApi'
import { monitoringApi } from '@/api'
import { Card, CardHeader, Badge, StatusDot, LoadingOverlay, ErrorBanner, EmptyState } from '@/components/ui'

interface CeleryTask {
  id: string
  name: string
  args?: unknown[]
  kwargs?: Record<string, unknown>
  hostname?: string
  time_start?: number
}

function TaskRow({ task, statusColor }: { task: CeleryTask; statusColor: 'green' | 'yellow' | 'gray' }) {
  const name = typeof task.name === 'string'
    ? task.name.split('.').slice(-2).join('.')
    : 'unknown'

  return (
    <div className="flex items-center gap-4 px-5 py-3 hover:bg-slate-50 transition-colors">
      <StatusDot color={statusColor} pulse={statusColor === 'yellow'} />
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium text-slate-800 font-mono">{name}</p>
        <p className="text-xs text-slate-400 truncate mt-0.5">
          {task.hostname ?? '—'} · {task.id?.slice(0, 12)}…
        </p>
      </div>
    </div>
  )
}

function WorkerSection({ title, tasks, color, icon: Icon }: {
  title: string
  tasks: CeleryTask[]
  color: 'green' | 'yellow' | 'gray'
  icon: React.ElementType
}) {
  return (
    <Card>
      <CardHeader
        title={title}
        subtitle={`${tasks.length} task${tasks.length !== 1 ? 's' : ''}`}
        action={<Badge variant={tasks.length > 0 ? (color === 'green' ? 'green' : color === 'yellow' ? 'yellow' : 'gray') : 'gray'}>{tasks.length}</Badge>}
      />
      {tasks.length === 0 ? (
        <EmptyState
          icon={<Icon className="h-6 w-6" />}
          title={`No ${title.toLowerCase()}`}
        />
      ) : (
        <div className="divide-y divide-slate-50">
          {tasks.map((t) => (
            <TaskRow key={t.id} task={t} statusColor={color} />
          ))}
        </div>
      )}
    </Card>
  )
}

export default function JobsPage() {
  const { data, isLoading, error, refetch } = useApi(
    () => monitoringApi.jobs(),
    [],
    { pollInterval: 5_000 },
  )

  const activeTasks  = Object.values(data?.active   ?? {}).flat() as CeleryTask[]
  const reservedTasks = Object.values(data?.reserved ?? {}).flat() as CeleryTask[]
  const scheduledTasks = Object.values(data?.scheduled ?? {}).flat() as CeleryTask[]

  const workerNames = Object.keys({ ...(data?.active ?? {}), ...(data?.reserved ?? {}) })

  return (
    <div className="p-6 max-w-4xl mx-auto space-y-5 animate-fade-in">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-slate-900">Jobs</h1>
          <p className="text-sm text-slate-500 mt-0.5">Live Celery worker status · refreshes every 5s</p>
        </div>
        <button
          onClick={refetch}
          className="text-slate-400 hover:text-slate-700 transition-colors"
          title="Refresh"
        >
          <RotateCcw className="h-4 w-4" />
        </button>
      </div>

      {error && <ErrorBanner message={`Could not reach Celery broker: ${error}`} />}

      {/* Workers summary */}
      <Card className="p-5">
        <div className="flex items-center gap-3 mb-3">
          <Activity className="h-4 w-4 text-slate-400" />
          <p className="text-sm font-semibold text-slate-700">Workers online</p>
          <Badge variant={workerNames.length > 0 ? 'green' : 'red'}>{workerNames.length}</Badge>
        </div>
        {workerNames.length === 0 ? (
          <p className="text-xs text-slate-400">No workers detected. Is Celery running?</p>
        ) : (
          <div className="space-y-1.5">
            {workerNames.map((w) => (
              <div key={w} className="flex items-center gap-2 text-xs">
                <StatusDot color="green" pulse />
                <span className="text-slate-600 font-mono">{w}</span>
              </div>
            ))}
          </div>
        )}
      </Card>

      {isLoading && !data ? (
        <LoadingOverlay />
      ) : (
        <div className="space-y-4">
          <WorkerSection
            title="Active"
            tasks={activeTasks}
            color="green"
            icon={CheckCircle2}
          />
          <WorkerSection
            title="Queued"
            tasks={reservedTasks}
            color="yellow"
            icon={Clock}
          />
          <WorkerSection
            title="Scheduled"
            tasks={scheduledTasks}
            color="gray"
            icon={Clock}
          />
        </div>
      )}

      {data?.error && (
        <div className="bg-amber-50 border border-amber-200 rounded-lg p-4 text-sm text-amber-700">
          <XCircle className="h-4 w-4 inline mr-2" />
          Broker inspection error: {data.error}. Flower might be offline.
        </div>
      )}
    </div>
  )
}

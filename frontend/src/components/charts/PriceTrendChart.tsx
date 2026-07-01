import {
  ResponsiveContainer, AreaChart, Area, XAxis, YAxis,
  CartesianGrid, Tooltip, ReferenceLine,
} from 'recharts'
import { format, parseISO } from 'date-fns'
import type { PricePoint } from '@/types'

interface PriceTrendChartProps {
  data: PricePoint[]
  avgPrice?: number | null
  minPrice?: number | null
}

// Chart data point — PricePoint fields spread + formatted date string
interface ChartPoint extends PricePoint {
  date: string
}

interface TooltipEntry {
  payload?: ChartPoint
}

function CustomTooltip({ active, payload }: { active?: boolean; payload?: TooltipEntry[] }) {
  if (!active || !payload?.[0]?.payload) return null
  const d = payload[0].payload
  return (
    <div className="bg-surface-900 border border-surface-700 rounded-lg shadow-xl p-3 text-xs">
      <p className="text-slate-400 mb-1">{d.date}</p>
      <p className="text-white font-semibold text-sm">R$ {d.price?.toFixed(2)}</p>
      {d.price_changed && (
        <p className={`mt-0.5 font-medium ${(d.price_diff ?? 0) < 0 ? 'text-emerald-400' : 'text-red-400'}`}>
          {(d.price_diff ?? 0) > 0 ? '+' : ''}{d.price_diff?.toFixed(2)}
        </p>
      )}
    </div>
  )
}

export function PriceTrendChart({ data, avgPrice, minPrice }: PriceTrendChartProps) {
  const chartData: ChartPoint[] = data.map((p) => ({
    ...p,
    date: format(parseISO(p.scraped_at), 'dd/MM HH:mm'),
  }))

  const prices = data.map((d) => d.price)
  const yMin = Math.min(...prices) * 0.98
  const yMax = Math.max(...prices) * 1.02

  return (
    <ResponsiveContainer width="100%" height={220}>
      <AreaChart data={chartData} margin={{ top: 4, right: 4, left: 0, bottom: 0 }}>
        <defs>
          <linearGradient id="priceGrad" x1="0" y1="0" x2="0" y2="1">
            <stop offset="5%"  stopColor="#6366f1" stopOpacity={0.3} />
            <stop offset="95%" stopColor="#6366f1" stopOpacity={0.02} />
          </linearGradient>
        </defs>
        <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" vertical={false} />
        <XAxis
          dataKey="date"
          tick={{ fontSize: 10, fill: '#64748b' }}
          axisLine={false}
          tickLine={false}
          interval="preserveStartEnd"
        />
        <YAxis
          domain={[yMin, yMax]}
          tick={{ fontSize: 10, fill: '#64748b' }}
          axisLine={false}
          tickLine={false}
          tickFormatter={(v: number) => `R$${v.toFixed(0)}`}
          width={64}
        />
        <Tooltip content={<CustomTooltip />} />
        {avgPrice && (
          <ReferenceLine
            y={avgPrice}
            stroke="#94a3b8"
            strokeDasharray="4 4"
            label={{ value: 'avg', position: 'right', fontSize: 10, fill: '#94a3b8' }}
          />
        )}
        {minPrice && (
          <ReferenceLine
            y={minPrice}
            stroke="#34d399"
            strokeDasharray="4 4"
            label={{ value: 'min', position: 'right', fontSize: 10, fill: '#34d399' }}
          />
        )}
        <Area
          type="monotone"
          dataKey="price"
          stroke="#6366f1"
          strokeWidth={2}
          fill="url(#priceGrad)"
          dot={false}
          activeDot={{ r: 4, fill: '#6366f1', stroke: '#fff', strokeWidth: 2 }}
        />
      </AreaChart>
    </ResponsiveContainer>
  )
}

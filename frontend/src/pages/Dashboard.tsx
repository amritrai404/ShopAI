import { useEffect, useState } from 'react'
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from 'recharts'
import { api } from '../services/api'
import type { MonthlyTrendRow, ProfitSummary, RevenueSummary } from '../types'

function isoDaysAgo(days: number): string {
  const d = new Date()
  d.setDate(d.getDate() - days)
  return d.toISOString().slice(0, 10)
}

export default function Dashboard() {
  const start = isoDaysAgo(30)
  const end = isoDaysAgo(0)

  const [revenue, setRevenue] = useState<RevenueSummary | null>(null)
  const [profit, setProfit] = useState<ProfitSummary | null>(null)
  const [trend, setTrend] = useState<MonthlyTrendRow[]>([])
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    Promise.all([api.revenue(start, end), api.profit(start, end), api.monthlyTrend(start, end)])
      .then(([r, p, t]) => {
        setRevenue(r)
        setProfit(p)
        setTrend(t)
      })
      .catch((e) => setError(e.message))
  }, [])

  if (error) return <div className="p-6 text-red-600">Error: {error}</div>
  if (!revenue || !profit) return <div className="p-6">Loading…</div>

  const fmt = (v: string) => `₹${parseFloat(v).toLocaleString('en-IN', { maximumFractionDigits: 2 })}`

  const chartData = trend.map((r) => ({
    month: r.month?.slice(0, 7) ?? '',
    net: parseFloat(r.net),
  }))

  return (
    <div className="p-6">
      <h1 className="text-2xl font-bold mb-1">Dashboard</h1>
      <p className="text-slate-500 mb-6 text-sm">
        Last 30 days · {start} → {end}
      </p>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
        <div className="bg-white rounded-lg p-4 shadow-sm">
          <div className="text-xs text-slate-500 mb-1">Net Revenue</div>
          <div className="text-2xl font-bold">{fmt(revenue.net_revenue)}</div>
          <div className="text-xs text-slate-500 mt-1">{revenue.transaction_count} transactions</div>
        </div>
        <div className="bg-white rounded-lg p-4 shadow-sm">
          <div className="text-xs text-slate-500 mb-1">Gross Profit</div>
          <div className="text-2xl font-bold">{fmt(profit.gross_profit)}</div>
          <div className="text-xs text-slate-500 mt-1">{profit.gross_margin_pct}% margin</div>
        </div>
        <div className="bg-white rounded-lg p-4 shadow-sm">
          <div className="text-xs text-slate-500 mb-1">Operating Profit</div>
          <div className="text-2xl font-bold">{fmt(profit.operating_profit)}</div>
          <div className="text-xs text-slate-500 mt-1">{profit.operating_margin_pct}% margin</div>
        </div>
      </div>

      <div className="bg-white rounded-lg p-4 shadow-sm">
        <div className="text-sm font-semibold mb-3">Monthly Net Revenue</div>
        <ResponsiveContainer width="100%" height={260}>
          <LineChart data={chartData}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="month" />
            <YAxis />
            <Tooltip formatter={(v: number) => fmt(String(v))} />
            <Line type="monotone" dataKey="net" stroke="#0f172a" strokeWidth={2} />
          </LineChart>
        </ResponsiveContainer>
      </div>

      {!profit.data_complete && (
        <div className="mt-4 p-3 bg-yellow-50 border border-yellow-200 rounded text-sm">
          <strong>Data note:</strong> {profit.notes.join(' · ')}
        </div>
      )}
    </div>
  )
}
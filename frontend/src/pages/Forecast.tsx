import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from 'recharts'
import { TrendingUp, AlertCircle } from 'lucide-react'
import { useForecast } from '../hooks/useForecast'

export default function Forecast() {
  const { data, loading, error } = useForecast(7)

  if (loading) return <div className="p-6">Loading forecast...</div>
  if (error) return (
    <div className="p-6 text-red-600 flex items-center gap-2">
      <AlertCircle size={18} /> Error: {error}
    </div>
  )
  if (!data || data.points.length === 0) return <div className="p-6">No forecast data available.</div>

  const chartData = data.points.map(p => ({
    date: new Date(p.date).toLocaleDateString('en-IN', { day: 'numeric', month: 'short' }),
    revenue: p.predicted_revenue
  }))

  return (
    <div className="p-6 max-w-4xl mx-auto">
      <div className="flex items-center gap-2 mb-6">
        <TrendingUp className="text-slate-700" size={24} />
        <h1 className="text-2xl font-bold">7-Day Forecast</h1>
      </div>

      <div className="bg-white p-6 rounded-lg shadow-sm">
        <ResponsiveContainer width="100%" height={300}>
          <LineChart data={chartData}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="date" />
            <YAxis tickFormatter={(val) => `₹${val}`} />
            <Tooltip formatter={(val: number) => [`₹${val.toFixed(2)}`, 'Predicted Revenue']} />
            <Line type="monotone" dataKey="revenue" stroke="#0f172a" strokeWidth={2} dot={{ r: 4 }} />
          </LineChart>
        </ResponsiveContainer>
      </div>
      
      <p className="mt-4 text-sm text-slate-500">
        Model: {data.model_version || 'N/A'} · Generated: {data.generated_at ? new Date(data.generated_at).toLocaleString() : 'N/A'}
      </p>
    </div>
  )
}
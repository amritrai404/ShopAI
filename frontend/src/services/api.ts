import type {
  ChatResponse,
  ForecastResponse,
  LowStockItem,
  MonthlyTrendRow,
  ProductPerformance,
  ProfitSummary,
  RevenueSummary,
} from '../types'

const BASE = '/api'

async function get<T>(path: string, params?: Record<string, string | number>): Promise<T> {
  const url = new URL(BASE + path, window.location.origin)
  if (params) {
    Object.entries(params).forEach(([k, v]) => url.searchParams.set(k, String(v)))
  }
  const res = await fetch(url.pathname + url.search)
  if (!res.ok) {
    const body = await res.text()
    throw new Error(`API ${res.status}: ${body}`)
  }
  return res.json()
}

async function post<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(BASE + path, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  if (!res.ok) {
    const text = await res.text()
    throw new Error(`API ${res.status}: ${text}`)
  }
  return res.json()
}

export const api = {
  health: () => get<{ status: string; app: string }>('/health'),
  revenue: (start: string, end: string) =>
    get<RevenueSummary>('/analytics/revenue', { start, end }),
  profit: (start: string, end: string) =>
    get<ProfitSummary>('/analytics/profit', { start, end }),
  topProducts: (limit = 5, by: 'revenue' | 'units' = 'revenue') =>
    get<ProductPerformance[]>('/analytics/top-products', { limit, by }),
  lowStock: (threshold = 50) =>
    get<LowStockItem[]>('/analytics/low-stock', { threshold }),
  monthlyTrend: (start: string, end: string) =>
    get<MonthlyTrendRow[]>('/analytics/monthly-trend', { start, end }),
  forecast: (days = 7) => get<ForecastResponse>('/forecast', { days }),
  chat: (message: string, sessionId?: string | null) =>
    post<ChatResponse>('/chat', { message, session_id: sessionId ?? null, mode: 'local' }),
  
  // Naya CSV Upload function add kiya gaya hai
  uploadCsv: async (file: File) => {
    const formData = new FormData()
    formData.append('file', file)
    const res = await fetch('/api/data/upload', {
      method: 'POST',
      body: formData,
    })
    if (!res.ok) {
      const text = await res.text()
      throw new Error(`Upload failed: ${text}`)
    }
    return res.json() as Promise<{ filename: string; rows_processed: number; status: string }>
  },
}
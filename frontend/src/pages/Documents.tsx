import { useState } from 'react'
import { FileText, Search, Upload } from 'lucide-react'

export default function Documents() {
  const [file, setFile] = useState<File | null>(null)
  const [query, setQuery] = useState('')
  const [results, setResults] = useState<any[]>([])
  const [loading, setLoading] = useState(false)

  const handleUpload = async () => {
    if (!file) return
    setLoading(true)
    const formData = new FormData()
    formData.append('file', file)
    try {
      await fetch('/api/documents/upload', { method: 'POST', body: formData })
      alert('Document uploaded successfully!')
      setFile(null)
    } catch (err) {
      alert('Upload failed')
    } finally {
      setLoading(false)
    }
  }

  const handleSearch = async () => {
    if (!query) return
    setLoading(true)
    try {
      const res = await fetch(`/api/documents/search?q=${encodeURIComponent(query)}`)
      const data = await res.json()
      setResults(data)
    } catch (err) {
      alert('Search failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="p-6 max-w-4xl mx-auto">
      <h1 className="text-2xl font-bold mb-6 flex items-center gap-2">
        <FileText /> Documents
      </h1>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
        <div className="bg-white p-6 rounded-lg shadow-sm">
          <h2 className="font-semibold mb-4 flex items-center gap-2"><Upload size={18} /> Upload PDF</h2>
          <input type="file" accept=".pdf" onChange={(e) => setFile(e.target.files?.[0] || null)} className="mb-4 block w-full text-sm" />
          <button onClick={handleUpload} disabled={!file || loading} className="bg-slate-900 text-white px-4 py-2 rounded-lg w-full disabled:opacity-50">
            {loading ? 'Uploading...' : 'Upload Document'}
          </button>
        </div>

        <div className="bg-white p-6 rounded-lg shadow-sm">
          <h2 className="font-semibold mb-4 flex items-center gap-2"><Search size={18} /> Search Documents</h2>
          <div className="flex gap-2">
            <input type="text" value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Search text..." className="flex-1 border rounded-lg px-3 py-2 text-sm" />
            <button onClick={handleSearch} disabled={loading} className="bg-slate-900 text-white px-4 py-2 rounded-lg text-sm disabled:opacity-50">Search</button>
          </div>
        </div>
      </div>

      {results.length > 0 && (
        <div className="bg-white p-6 rounded-lg shadow-sm">
          <h2 className="font-semibold mb-4">Search Results</h2>
          <div className="space-y-4">
            {results.map((r, i) => (
              <div key={i} className="p-4 bg-slate-50 rounded-lg border border-slate-100">
                <p className="text-sm text-slate-700">{r.text}</p>
                <p className="text-xs text-slate-500 mt-2">Score: {r.score?.toFixed(3)}</p>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
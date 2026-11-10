import { useState } from 'react'
import { Upload as UploadIcon, CheckCircle, AlertCircle } from 'lucide-react'
import { api } from '../services/api' // Naya API import add kiya

export default function Upload() {
  const [file, setFile] = useState<File | null>(null)
  const [status, setStatus] = useState<'idle' | 'uploading' | 'success' | 'error'>('idle')
  const [message, setMessage] = useState('')

  const handleUpload = async () => {
    if (!file) return
    setStatus('uploading')
    setMessage('')

    try {
      const res = await api.uploadCsv(file)
      setStatus('success')
      setMessage(`File uploaded! Processed ${res.rows_processed} rows.`)
    } catch (err) {
      setStatus('error')
      setMessage(err instanceof Error ? err.message : 'Unknown error')
    }
  }

  return (
    <div className="p-6 max-w-2xl mx-auto">
      <h1 className="text-2xl font-bold mb-6">Upload Sales Data</h1>
      
      <div className="bg-white p-8 rounded-lg shadow-sm border-2 border-dashed border-slate-300 text-center">
        <UploadIcon className="mx-auto text-slate-400 mb-4" size={48} />
        <p className="text-slate-600 mb-2">Drag and drop your CSV file here, or click to browse</p>
        <input 
          type="file" 
          accept=".csv"
          onChange={(e) => setFile(e.target.files?.[0] || null)}
          className="block w-full text-sm text-slate-500 file:mr-4 file:py-2 file:px-4 file:rounded-full file:border-0 file:text-sm file:font-semibold file:bg-slate-100 file:text-slate-700 hover:file:bg-slate-200"
        />
      </div>

      {file && (
        <div className="mt-6 flex items-center justify-between bg-slate-50 p-4 rounded-lg">
          <span className="text-sm font-medium">{file.name} ({(file.size / 1024).toFixed(1)} KB)</span>
          <button 
            onClick={handleUpload}
            disabled={status === 'uploading'}
            className="bg-slate-900 text-white px-4 py-2 rounded-lg text-sm disabled:opacity-50"
          >
            {status === 'uploading' ? 'Uploading...' : 'Upload File'}
          </button>
        </div>
      )}

      {status === 'success' && (
        <div className="mt-4 p-4 bg-green-50 text-green-700 rounded-lg flex items-center gap-2">
          <CheckCircle size={18} /> {message}
        </div>
      )}
      {status === 'error' && (
        <div className="mt-4 p-4 bg-red-50 text-red-700 rounded-lg flex items-center gap-2">
          <AlertCircle size={18} /> {message}
        </div>
      )}
    </div>
  )
}
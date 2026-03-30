'use client'
import { useEffect, useRef, useState } from 'react'
import { createClient } from '@/lib/supabase'

const API = process.env.NEXT_PUBLIC_API_URL ?? ''

const PRODUCT_CATEGORIES = [
  { id: 'stone_management', label: 'Stone Management' },
  { id: 'bph', label: 'BPH' },
  { id: 'bladder_health', label: 'Bladder Health' },
  { id: 'capital_equipment', label: 'Capital Equipment' },
  { id: 'health_economics', label: 'Health Economics' },
]

interface LibraryItem {
  id: string
  name: string
  description?: string
  category?: string
  stage_count?: number
  approved: boolean
}

interface UploadedFile {
  id: string
  filename: string
  uploaded_at: string
  chunk_count: number
  status: 'processing' | 'ready' | 'error'
}

function ApprovedBadge() {
  return (
    <span
      className="text-[9px] font-bold px-1.5 py-0.5 rounded uppercase tracking-wider"
      style={{ background: 'rgba(45,219,222,0.12)', color: '#2ddbde' }}
    >
      Approved
    </span>
  )
}

function UnverifiedBadge() {
  return (
    <span
      className="text-[9px] font-bold px-1.5 py-0.5 rounded uppercase tracking-wider"
      style={{ background: 'rgba(146,64,14,0.2)', color: '#fbbf24' }}
    >
      Unverified
    </span>
  )
}

export default function ContentLibrary() {
  const [activeCategory, setActiveCategory] = useState('stone_management')
  const [items, setItems] = useState<LibraryItem[]>([])
  const [uploads, setUploads] = useState<UploadedFile[]>([])
  const [dragging, setDragging] = useState(false)
  const [uploading, setUploading] = useState(false)
  const [uploadProgress, setUploadProgress] = useState<string | null>(null)
  const [token, setToken] = useState<string | null>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    const supabase = createClient()
    supabase.auth.getSession().then(({ data: { session } }) => {
      if (!session) return
      setToken(session.access_token)
      const headers = { Authorization: `Bearer ${session.access_token}` }
      fetch(`${API}/api/series`, { headers })
        .then(r => r.ok ? r.json() : null)
        .then(data => { if (data?.series) setItems(data.series) })
        .catch(() => {})
      fetch(`${API}/api/uploads`, { headers })
        .then(r => r.ok ? r.json() : null)
        .then(data => { if (Array.isArray(data)) setUploads(data) })
        .catch(() => {})
    })
  }, [])

  const filteredItems = items.filter(item =>
    !item.category || item.category === activeCategory
  )

  async function handleFiles(files: FileList | null) {
    if (!files || files.length === 0 || !token) return
    const file = files[0]
    const allowed = [
      'application/pdf',
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
      'text/plain',
    ]
    if (!allowed.includes(file.type)) {
      setUploadProgress('Only PDF, DOCX, and TXT files are accepted.')
      setTimeout(() => setUploadProgress(null), 4000)
      return
    }
    if (file.size > 10 * 1024 * 1024) {
      setUploadProgress('File exceeds 10 MB limit.')
      setTimeout(() => setUploadProgress(null), 4000)
      return
    }
    setUploading(true)
    setUploadProgress('Uploading...')
    const formData = new FormData()
    formData.append('file', file)
    try {
      const res = await fetch(`${API}/api/uploads`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` },
        body: formData,
      })
      if (!res.ok) throw new Error(`Upload failed: ${res.status}`)
      const data = await res.json()
      setUploadProgress(`Uploaded -- ${data.chunk_count ?? '...'} chunks indexed`)
      setUploads(prev => [data, ...prev])
      setTimeout(() => setUploadProgress(null), 5000)
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Upload failed'
      setUploadProgress(msg)
      setTimeout(() => setUploadProgress(null), 5000)
    } finally {
      setUploading(false)
    }
  }

  async function deleteUpload(id: string) {
    if (!token) return
    try {
      await fetch(`${API}/api/uploads/${id}`, {
        method: 'DELETE',
        headers: { Authorization: `Bearer ${token}` },
      })
      setUploads(prev => prev.filter(u => u.id !== id))
    } catch {/* silent */}
  }

  return (
    <div className="flex flex-col md:flex-row gap-4 w-full min-h-0">

      <div className="flex-1 bg-[#1c2026] rounded-lg overflow-hidden flex flex-col md:flex-row">
        <div className="flex md:flex-col gap-0 border-b md:border-b-0 md:border-r border-white/[0.06] md:min-w-[180px] overflow-x-auto md:overflow-x-visible">
          {PRODUCT_CATEGORIES.map(cat => (
            <button
              key={cat.id}
              onClick={() => setActiveCategory(cat.id)}
              className={`px-4 py-3 text-left text-[12px] font-semibold whitespace-nowrap transition-colors flex-shrink-0 ${
                activeCategory === cat.id
                  ? 'text-[#2ddbde] bg-[#2ddbde]/[0.06] border-b-2 md:border-b-0 md:border-l-2 border-[#2ddbde]'
                  : 'text-[#9aa0a6] hover:text-[#e8eaed] hover:bg-[#353940]'
              }`}
            >
              {cat.label}
            </button>
          ))}
        </div>

        <div className="flex-1 p-4 overflow-y-auto">
          <p className="text-[10px] uppercase tracking-widest text-[#5f6368] font-semibold mb-3">
            Admin Library -- {PRODUCT_CATEGORIES.find(c => c.id === activeCategory)?.label}
          </p>
          {filteredItems.length === 0 ? (
            <div className="py-8 text-center">
              <p className="text-sm text-[#9aa0a6]">No scenarios in this category yet.</p>
              <p className="text-[11px] text-[#5f6368] mt-1">Content is managed by your administrator.</p>
            </div>
          ) : (
            <div className="space-y-2">
              {filteredItems.map(item => (
                <div
                  key={item.id}
                  className="flex items-center justify-between gap-3 p-3 rounded-lg hover:bg-[#353940] transition-colors"
                  style={{ background: '#181c22' }}
                >
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-2 mb-0.5">
                      <p className="text-[13px] font-semibold text-[#e8eaed] truncate">{item.name}</p>
                      <ApprovedBadge />
                    </div>
                    {item.description && (
                      <p className="text-[11px] text-[#5f6368] truncate">{item.description}</p>
                    )}
                    {item.stage_count && (
                      <p className="text-[10px] text-[#5f6368] mt-0.5">{item.stage_count} stages</p>
                    )}
                  </div>
                  <a
                    href={`/session/new?series=${item.id}`}
                    className="btn-primary-gradient flex-shrink-0 text-[11px] font-semibold px-3 py-1.5 rounded-lg"
                  >
                    Practice
                  </a>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      <div className="w-full md:w-80 bg-[#1c2026] rounded-lg p-4 flex flex-col gap-4">
        <div>
          <p className="text-sm font-semibold text-[#e8eaed]">My Materials</p>
          <p className="text-[11px] text-[#5f6368] mt-0.5">
            Personal practice only -- not used in certification sessions.
          </p>
        </div>

        <div
          onDragOver={e => { e.preventDefault(); setDragging(true) }}
          onDragLeave={() => setDragging(false)}
          onDrop={e => {
            e.preventDefault()
            setDragging(false)
            handleFiles(e.dataTransfer.files)
          }}
          onClick={() => fileInputRef.current?.click()}
          className={`rounded-lg border border-dashed flex flex-col items-center justify-center gap-2 py-8 cursor-pointer transition-colors ${
            dragging ? 'border-[#2ddbde] bg-[#2ddbde]/[0.05]' : 'border-white/[0.15] hover:border-[#2ddbde]/50'
          }`}
        >
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" style={{ color: '#2ddbde' }}>
            <path d="M12 15V3m0 0L8 7m4-4 4 4" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
            <path d="M3 15v4a2 2 0 002 2h14a2 2 0 002-2v-4" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/>
          </svg>
          <p className="text-[12px] font-medium text-[#9aa0a6]">
            {uploading ? 'Uploading...' : 'Drop file or click to browse'}
          </p>
          <p className="text-[10px] text-[#5f6368]">PDF, DOCX, TXT -- max 10 MB</p>
        </div>
        <input
          ref={fileInputRef}
          type="file"
          accept=".pdf,.docx,.txt,application/pdf,text/plain,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
          className="hidden"
          onChange={e => handleFiles(e.target.files)}
        />

        {uploadProgress && (
          <p className={`text-[11px] font-medium ${
            uploadProgress.toLowerCase().includes('fail') || uploadProgress.toLowerCase().includes('limit') || uploadProgress.toLowerCase().includes('only')
              ? 'text-red-400'
              : 'text-[#2ddbde]'
          }`}>{uploadProgress}</p>
        )}

        {uploads.length > 0 && (
          <div className="space-y-2">
            <p className="text-[10px] uppercase tracking-widest text-[#5f6368] font-semibold">Uploaded</p>
            {uploads.map(u => (
              <div
                key={u.id}
                className="flex items-center gap-2 p-2.5 rounded-lg"
                style={{ background: '#181c22' }}
              >
                <div className="flex-1 min-w-0">
                  <p className="text-[12px] font-medium text-[#e8eaed] truncate">{u.filename}</p>
                  <div className="flex items-center gap-1.5 mt-0.5">
                    <UnverifiedBadge />
                    <span className="font-mono text-[9px] text-[#5f6368]">
                      {u.chunk_count} chunks -- {new Date(u.uploaded_at).toLocaleDateString(undefined, { month: 'short', day: 'numeric' })}
                    </span>
                  </div>
                </div>
                <button
                  onClick={() => deleteUpload(u.id)}
                  className="text-[#5f6368] hover:text-red-400 transition-colors flex-shrink-0 p-1"
                  title="Remove upload"
                  aria-label="Delete uploaded file"
                >
                  <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
                    <path d="M2 2l10 10M12 2L2 12" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/>
                  </svg>
                </button>
              </div>
            ))}
          </div>
        )}

        {uploads.length === 0 && !uploading && (
          <div className="py-4 text-center">
            <p className="text-[11px] text-[#5f6368]">No files uploaded yet.</p>
          </div>
        )}
      </div>
    </div>
  )
}

'use client'
import { useState, useRef } from 'react'

const DOMAINS = ['product', 'clinical', 'cof', 'objection', 'compliance', 'stakeholder']

interface Props { productId: string; onIngested?: () => void }

export function KBUploadTab({ productId, onIngested }: Props) {
  const [proposed, setProposed] = useState<any[]>([])
  const [uploading, setUploading] = useState(false)
  const [form, setForm] = useState({
    domain: 'product',
    section: '',
    content: '',
    approved_claim: false,
    keywords: '',
  })
  const fileRef = useRef<HTMLInputElement>(null)

  async function handleFile(file: File) {
    setUploading(true)
    const fd = new FormData()
    fd.append('file', file)
    const res = await fetch(`/admin/knowledge-base/${productId}/upload`, { method: 'POST', body: fd })
    const data = await res.json()
    setProposed(data.proposed_chunks || [])
    setUploading(false)
  }

  async function ingestChunk(chunk: any) {
    await fetch(`/admin/knowledge-base/${productId}/chunks`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        ...chunk,
        keywords:
          typeof chunk.keywords === 'string'
            ? chunk.keywords.split(',').map((k: string) => k.trim())
            : chunk.keywords,
      }),
    })
  }

  async function ingestAll() {
    for (const chunk of proposed.filter(c => c._keep !== false)) await ingestChunk(chunk)
    setProposed([])
    onIngested?.()
  }

  async function submitManual(e: React.FormEvent) {
    e.preventDefault()
    await ingestChunk({ ...form, keywords: form.keywords.split(',').map(k => k.trim()) })
    setForm({ domain: 'product', section: '', content: '', approved_claim: false, keywords: '' })
    onIngested?.()
  }

  return (
    <div className="space-y-6">
      <div
        onDragOver={e => e.preventDefault()}
        onDrop={e => {
          e.preventDefault()
          const f = e.dataTransfer.files[0]
          if (f) handleFile(f)
        }}
        className="border-2 border-dashed border-slate-600 rounded-lg p-10 text-center cursor-pointer hover:border-slate-400 transition-colors"
        onClick={() => fileRef.current?.click()}
      >
        <div className="text-3xl mb-2">&#128194;</div>
        <p className="text-slate-200 font-medium">Drop any file here</p>
        <p className="text-slate-500 text-sm mt-1">
          PDF &middot; DOCX &middot; TXT &middot; JPG &middot; PNG &middot; TIFF &middot; PPTX &middot; XLSX &middot; RTF &middot; and more
        </p>
        <input
          ref={fileRef}
          type="file"
          className="hidden"
          onChange={e => {
            const f = e.target.files?.[0]
            if (f) handleFile(f)
          }}
        />
      </div>

      {proposed.length > 0 && (
        <div className="space-y-3">
          <div className="flex justify-between items-center">
            <h3 className="font-medium text-sm">
              {proposed.length} chunks proposed &mdash; review before ingesting
            </h3>
            <button
              onClick={ingestAll}
              className="bg-emerald-500 text-black text-sm font-semibold px-4 py-1.5 rounded"
            >
              Ingest {proposed.filter(c => c._keep !== false).length} chunks &rarr;
            </button>
          </div>
          {proposed.map((chunk, i) => (
            <div
              key={i}
              className={`bg-slate-800 rounded-lg p-4 border ${
                chunk._keep === false ? 'opacity-40 border-slate-700' : 'border-slate-600'
              }`}
            >
              <div className="flex gap-3 mb-3 flex-wrap items-center">
                <select
                  value={chunk.domain}
                  onChange={e => {
                    const p = [...proposed]
                    p[i] = { ...p[i], domain: e.target.value }
                    setProposed(p)
                  }}
                  className="bg-slate-700 text-sm rounded px-2 py-1"
                >
                  {DOMAINS.map(d => (
                    <option key={d}>{d}</option>
                  ))}
                </select>
                <input
                  value={chunk.section || ''}
                  placeholder="section"
                  onChange={e => {
                    const p = [...proposed]
                    p[i] = { ...p[i], section: e.target.value }
                    setProposed(p)
                  }}
                  className="bg-slate-700 text-sm rounded px-2 py-1 w-32"
                />
                <label className="flex items-center gap-2 text-xs text-amber-400">
                  <input
                    type="checkbox"
                    checked={!!chunk.approved_claim}
                    onChange={e => {
                      const p = [...proposed]
                      p[i] = { ...p[i], approved_claim: e.target.checked }
                      setProposed(p)
                    }}
                  />
                  FDA-cleared / approved claim
                </label>
                <span className="ml-auto text-xs text-slate-500">
                  {chunk.content.split(' ').length} words
                </span>
              </div>
              <p className="text-xs text-slate-400 line-clamp-3">{chunk.content}</p>
              <div className="flex gap-2 mt-3">
                <button
                  onClick={() => {
                    const p = [...proposed]
                    p[i] = { ...p[i], _keep: true }
                    setProposed(p)
                  }}
                  className="text-xs bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 px-3 py-1 rounded"
                >
                  Keep
                </button>
                <button
                  onClick={() => {
                    const p = [...proposed]
                    p[i] = { ...p[i], _keep: false }
                    setProposed(p)
                  }}
                  className="text-xs text-red-400 border border-red-400/30 px-3 py-1 rounded"
                >
                  Discard
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      <div>
        <div className="flex items-center gap-3 my-4">
          <div className="flex-1 h-px bg-slate-800" />
          <span className="text-xs text-slate-600">or add a chunk manually</span>
          <div className="flex-1 h-px bg-slate-800" />
        </div>
        <form onSubmit={submitManual} className="space-y-3">
          <div className="grid grid-cols-3 gap-3">
            <div>
              <label className="text-xs text-slate-500 block mb-1" htmlFor="domain">
                Domain
              </label>
              <select
                id="domain"
                value={form.domain}
                onChange={e => setForm({ ...form, domain: e.target.value })}
                className="w-full bg-slate-800 border border-slate-700 rounded px-2 py-1.5 text-sm"
              >
                {DOMAINS.map(d => (
                  <option key={d}>{d}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="text-xs text-slate-500 block mb-1">Section</label>
              <input
                value={form.section}
                onChange={e => setForm({ ...form, section: e.target.value })}
                placeholder="e.g. moa, claims"
                className="w-full bg-slate-800 border border-slate-700 rounded px-2 py-1.5 text-sm"
              />
            </div>
            <div className="flex flex-col justify-end">
              <label
                className="flex items-center gap-2 text-xs text-amber-400 pb-1.5 cursor-pointer"
                htmlFor="approved"
              >
                <input
                  id="approved"
                  type="checkbox"
                  checked={form.approved_claim}
                  onChange={e => setForm({ ...form, approved_claim: e.target.checked })}
                  className="w-3.5 h-3.5"
                />
                FDA-cleared / approved claim
              </label>
            </div>
          </div>
          <div>
            <label className="text-xs text-slate-500 block mb-1">
              Keywords (comma-separated)
            </label>
            <input
              value={form.keywords}
              onChange={e => setForm({ ...form, keywords: e.target.value })}
              placeholder="encrustation, PercuShield, 59 percent"
              className="w-full bg-slate-800 border border-slate-700 rounded px-2 py-1.5 text-sm"
            />
          </div>
          <div>
            <label className="text-xs text-slate-500 block mb-1">
              Content <span className="text-slate-600">(150-400 words)</span>
            </label>
            <textarea
              value={form.content}
              onChange={e => setForm({ ...form, content: e.target.value })}
              rows={5}
              className="w-full bg-slate-800 border border-slate-700 rounded px-2 py-2 text-sm resize-y"
            />
          </div>
          <div className="flex justify-end gap-2">
            <button
              type="button"
              onClick={() =>
                setForm({ domain: 'product', section: '', content: '', approved_claim: false, keywords: '' })
              }
              className="text-sm text-slate-400 border border-slate-700 px-4 py-1.5 rounded"
            >
              Clear
            </button>
            <button
              type="submit"
              className="text-sm bg-emerald-500 text-black font-semibold px-4 py-1.5 rounded"
            >
              Add to Knowledge Base + Ingest
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

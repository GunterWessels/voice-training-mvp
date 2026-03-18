'use client'
import { useEffect, useState } from 'react'

const DOMAINS = ['product', 'clinical', 'cof', 'objection', 'compliance', 'stakeholder']
const DOMAIN_COLORS: Record<string, string> = {
  product: 'bg-blue-500/15 text-blue-400',
  clinical: 'bg-emerald-500/15 text-emerald-400',
  cof: 'bg-amber-500/15 text-amber-400',
  objection: 'bg-purple-500/15 text-purple-400',
  compliance: 'bg-red-500/15 text-red-400',
  stakeholder: 'bg-cyan-500/15 text-cyan-400',
}

export function KBManageTab({ productId }: { productId: string }) {
  const [chunks, setChunks] = useState<any[]>([])
  const [editingId, setEditingId] = useState<string | null>(null)
  const [editForm, setEditForm] = useState<any>(null)

  useEffect(() => {
    fetch(`/admin/knowledge-base/${productId}/chunks`)
      .then(r => r.json())
      .then(d => setChunks(d.chunks || []))
  }, [productId])

  async function deleteChunk(id: string) {
    await fetch(`/admin/knowledge-base/${productId}/chunks/${id}`, { method: 'DELETE' })
    setChunks(c => c.filter(ch => ch.id !== id))
  }

  function startEdit(chunk: any) {
    setEditingId(chunk.id)
    setEditForm({
      domain: chunk.domain,
      section: chunk.section || '',
      content: chunk.content,
      approved_claim: chunk.approved_claim,
      keywords: (chunk.keywords || []).join(', '),
      source_doc: chunk.source_doc || '',
    })
  }

  async function saveEdit(id: string) {
    const payload = {
      ...editForm,
      keywords: editForm.keywords
        .split(',')
        .map((k: string) => k.trim())
        .filter(Boolean),
    }
    const res = await fetch(`/admin/knowledge-base/${productId}/chunks/${id}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    })
    if (res.ok) {
      setChunks(c => c.map(ch => (ch.id === id ? { ...ch, ...payload } : ch)))
      setEditingId(null)
      setEditForm(null)
    }
  }

  async function reingestAll() {
    await fetch(`/admin/knowledge-base/${productId}/reingest`, { method: 'POST' })
  }

  return (
    <div>
      <table className="w-full text-xs border-collapse">
        <thead>
          <tr className="bg-slate-800/50">
            {['ID', 'Domain', 'Section', 'Approved Claim', 'Preview', 'Actions'].map(h => (
              <th
                key={h}
                className="text-left px-3 py-2.5 text-slate-500 border-b border-slate-800 font-medium"
              >
                {h}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {chunks.map(chunk => (
            <>
              <tr key={chunk.id} className="border-b border-slate-800/60 hover:bg-slate-800/30">
                <td className="px-3 py-2.5 text-slate-500 font-mono">{chunk.id}</td>
                <td className="px-3 py-2.5">
                  <span className={`px-2 py-0.5 rounded text-xs ${DOMAIN_COLORS[chunk.domain] || ''}`}>
                    {chunk.domain}
                  </span>
                </td>
                <td className="px-3 py-2.5 text-slate-400">{chunk.section || '—'}</td>
                <td className="px-3 py-2.5">
                  {chunk.approved_claim ? (
                    <span className="text-amber-400">Yes</span>
                  ) : (
                    <span className="text-slate-600">—</span>
                  )}
                </td>
                <td className="px-3 py-2.5 text-slate-500 max-w-xs truncate">
                  {chunk.content?.slice(0, 100)}…
                </td>
                <td className="px-3 py-2.5 flex gap-3">
                  <button onClick={() => startEdit(chunk)} className="text-blue-400 hover:text-blue-300">
                    Edit
                  </button>
                  <button
                    onClick={() => deleteChunk(chunk.id)}
                    className="text-red-400 hover:text-red-300"
                  >
                    Delete
                  </button>
                </td>
              </tr>
              {editingId === chunk.id && editForm && (
                <tr key={chunk.id + '-edit'} className="bg-slate-800/60 border-b border-slate-700">
                  <td colSpan={6} className="px-4 py-4">
                    <div className="grid grid-cols-3 gap-3 mb-3">
                      <div>
                        <label className="text-xs text-slate-500 block mb-1">Domain</label>
                        <select
                          value={editForm.domain}
                          onChange={e => setEditForm({ ...editForm, domain: e.target.value })}
                          className="w-full bg-slate-700 rounded px-2 py-1 text-xs"
                        >
                          {DOMAINS.map(d => (
                            <option key={d}>{d}</option>
                          ))}
                        </select>
                      </div>
                      <div>
                        <label className="text-xs text-slate-500 block mb-1">Section</label>
                        <input
                          value={editForm.section}
                          onChange={e => setEditForm({ ...editForm, section: e.target.value })}
                          className="w-full bg-slate-700 rounded px-2 py-1 text-xs"
                        />
                      </div>
                      <div className="flex items-end pb-1">
                        <label className="flex items-center gap-2 text-xs text-amber-400 cursor-pointer">
                          <input
                            type="checkbox"
                            checked={editForm.approved_claim}
                            onChange={e =>
                              setEditForm({ ...editForm, approved_claim: e.target.checked })
                            }
                          />
                          FDA-cleared / approved claim
                        </label>
                      </div>
                    </div>
                    <div className="mb-3">
                      <label className="text-xs text-slate-500 block mb-1">
                        Keywords (comma-separated)
                      </label>
                      <input
                        value={editForm.keywords}
                        onChange={e => setEditForm({ ...editForm, keywords: e.target.value })}
                        className="w-full bg-slate-700 rounded px-2 py-1 text-xs"
                      />
                    </div>
                    <div className="mb-3">
                      <label className="text-xs text-slate-500 block mb-1">Content</label>
                      <textarea
                        value={editForm.content}
                        onChange={e => setEditForm({ ...editForm, content: e.target.value })}
                        rows={4}
                        className="w-full bg-slate-700 rounded px-2 py-1.5 text-xs resize-y"
                      />
                    </div>
                    <div className="flex gap-2 justify-end">
                      <button
                        onClick={() => {
                          setEditingId(null)
                          setEditForm(null)
                        }}
                        className="text-xs text-slate-400 border border-slate-700 px-3 py-1 rounded"
                      >
                        Cancel
                      </button>
                      <button
                        onClick={() => saveEdit(chunk.id)}
                        className="text-xs bg-emerald-500 text-black font-semibold px-3 py-1 rounded"
                      >
                        Save + Re-embed
                      </button>
                    </div>
                  </td>
                </tr>
              )}
            </>
          ))}
        </tbody>
      </table>
      <div className="flex justify-end mt-4">
        <button
          onClick={reingestAll}
          className="text-sm border border-slate-700 text-slate-400 px-4 py-1.5 rounded hover:border-slate-500"
        >
          Re-ingest All
        </button>
      </div>
    </div>
  )
}

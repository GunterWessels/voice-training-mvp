'use client'

import { useState, useRef } from 'react'

interface ParseResult {
  headers: string[]
  detected: Record<string, string>
  preview: Record<string, string>[]
  all_rows: Record<string, string>[]
  total_rows: number
}

interface Props {
  authHeader: Record<string, string>
  onImportComplete: (result: { created: number; skipped: number }) => void
}

const FIELD_OPTIONS = [
  { value: '', label: '— ignore —' },
  { value: 'email', label: 'Email' },
  { value: 'first_name', label: 'First Name' },
  { value: 'last_name', label: 'Last Name' },
  { value: 'name', label: 'Full Name' },
]

export default function AdminUploadFlow({ authHeader, onImportComplete }: Props) {
  const [showModal, setShowModal] = useState(false)
  const [step, setStep] = useState<'idle' | 'mapping' | 'importing' | 'done'>('idle')
  const [parseResult, setParseResult] = useState<ParseResult | null>(null)
  const [mapping, setMapping] = useState<Record<string, string>>({})
  const [sendInvites, setSendInvites] = useState(true)
  const [result, setResult] = useState<{ created: number; skipped: number } | null>(null)
  const [error, setError] = useState<string | null>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)
  const [loading, setLoading] = useState(false)

  function openModal() {
    setShowModal(true)
    setStep('idle')
    setError(null)
    setParseResult(null)
    setMapping({})
    setSendInvites(true)
    setResult(null)
  }

  function closeModal() {
    setShowModal(false)
    setStep('idle')
    setError(null)
    setParseResult(null)
    setMapping({})
    setSendInvites(true)
    setResult(null)
  }

  async function handleFileSelect(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0]
    if (!file) return

    setError(null)
    setLoading(true)

    try {
      const formData = new FormData()
      formData.append('file', file)

      const response = await fetch('/api/admin/users/parse-upload', {
        method: 'POST',
        headers: authHeader,
        body: formData,
      })

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}))
        throw new Error(errorData.error || `Upload failed: ${response.status}`)
      }

      const parsed: ParseResult = await response.json()
      setParseResult(parsed)

      // Pre-fill mapping from detected
      const initialMapping: Record<string, string> = {}
      for (const [field, header] of Object.entries(parsed.detected)) {
        initialMapping[header] = field
      }
      setMapping(initialMapping)

      setStep('mapping')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to parse file')
    } finally {
      setLoading(false)
      // Clear file input so same file can be re-selected
      if (fileInputRef.current) {
        fileInputRef.current.value = ''
      }
    }
  }

  async function handleImport() {
    if (!parseResult) return

    setLoading(true)
    setError(null)

    try {
      // Build rows from all_rows using mapping
      const rows = parseResult.all_rows.map(row => {
        const out: Record<string, string> = {}
        for (const [header, field] of Object.entries(mapping)) {
          if (field) {
            out[field] = row[header] ?? ''
          }
        }
        return out
      })

      const response = await fetch('/api/admin/users/bulk-import', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...authHeader,
        },
        body: JSON.stringify({
          rows,
          send_invites: sendInvites,
        }),
      })

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}))
        throw new Error(errorData.error || `Import failed: ${response.status}`)
      }

      const importResult = await response.json()
      setResult(importResult)
      setStep('done')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to import users')
      // Stay in mapping state to allow retry
    } finally {
      setLoading(false)
    }
  }

  const emailMapped = Object.values(mapping).includes('email')

  function handleDone() {
    if (result) {
      onImportComplete(result)
    }
    closeModal()
  }

  const inputClass = 'rounded-lg px-3 py-2 text-sm w-full bg-[#181c22] text-[#e8eaed] focus:outline-none focus:border-[#2ddbde] focus:ring-2 focus:ring-[#2ddbde]/30'

  return (
    <>
      <button
        onClick={openModal}
        className="btn-primary-gradient text-white text-sm font-semibold px-4 py-2 rounded-lg"
      >
        Upload List
      </button>

      {showModal && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4">
          <div
          className="bg-[#1c2026] rounded-xl shadow-lg p-6 w-full max-w-lg space-y-4"
          style={{ border: '1px solid rgba(255,255,255,0.08)' }}
          role="dialog"
          aria-modal="true"
          aria-labelledby="upload-modal-title"
        >
            {/* STEP 1: IDLE - File picker */}
            {step === 'idle' && (
              <>
                <h2 id="upload-modal-title" className="text-lg font-semibold text-[#e8eaed]">Upload User List</h2>
                <p className="text-sm text-[#9aa0a6]">
                  Upload a CSV, Excel, or TSV file with email and name columns.
                </p>

                <input
                  ref={fileInputRef}
                  type="file"
                  accept=".csv,.xlsx,.xls,.tsv"
                  onChange={handleFileSelect}
                  style={{ display: 'none' }}
                />

                {error && (
                  <div className="bg-red-500/15 border border-red-500/30 rounded-lg p-3">
                    <p className="text-sm text-red-400">{error}</p>
                  </div>
                )}

                <div className="flex gap-3 justify-end pt-4">
                  <button
                    type="button"
                    onClick={closeModal}
                    className="border-[#2ddbde] text-[#2ddbde] text-sm font-semibold px-4 py-2 rounded-lg hover:bg-[#353940]"
                    style={{ border: '1px solid #2ddbde' }}
                  >
                    Cancel
                  </button>
                  <button
                    type="button"
                    onClick={() => fileInputRef.current?.click()}
                    disabled={loading}
                    className="btn-primary-gradient text-white text-sm font-semibold px-4 py-2 rounded-lg disabled:opacity-50"
                  >
                    {loading ? 'Parsing…' : 'Upload List'}
                  </button>
                </div>
              </>
            )}

            {/* STEP 2: MAPPING - Column mapping + preview */}
            {step === 'mapping' && parseResult && (
              <>
                <h2 id="upload-modal-title" className="text-lg font-semibold text-[#e8eaed]">Map Columns</h2>
                <p className="text-sm text-[#9aa0a6]">
                  Assign columns from your file. Total rows: {parseResult.total_rows}
                </p>

                {error && (
                  <div className="bg-red-500/15 border border-red-500/30 rounded-lg p-3">
                    <p className="text-sm text-red-400">{error}</p>
                  </div>
                )}

                <div className="space-y-3 max-h-48 overflow-y-auto">
                  {parseResult.headers.map(header => (
                    <div key={header}>
                      <label className="block text-xs font-semibold text-[#9aa0a6] uppercase tracking-wide mb-1">
                        {header}
                      </label>
                      <select
                        value={mapping[header] || ''}
                        onChange={e =>
                          setMapping({
                            ...mapping,
                            [header]: e.target.value,
                          })
                        }
                        className={inputClass}
                        style={{ border: '1px solid rgba(255,255,255,0.08)' }}
                      >
                        {FIELD_OPTIONS.map(opt => (
                          <option key={opt.value} value={opt.value}>
                            {opt.label}
                          </option>
                        ))}
                      </select>
                    </div>
                  ))}
                </div>

                <div className="rounded-lg overflow-hidden" style={{ border: '1px solid rgba(255,255,255,0.08)' }}>
                  <table className="w-full text-xs">
                    <thead>
                      <tr className="bg-[#10141a]" style={{ borderBottom: '1px solid rgba(255,255,255,0.08)' }}>
                        {parseResult.headers.map(header => (
                          <th
                            key={header}
                            className="text-left px-3 py-2 font-semibold text-[#9aa0a6]"
                          >
                            {header}
                          </th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {parseResult.preview.slice(0, 5).map((row, idx) => (
                        <tr key={idx} className="hover:bg-[#353940] transition-colors" style={{ borderTop: '1px solid rgba(255,255,255,0.08)' }}>
                          {parseResult.headers.map(header => (
                            <td key={header} className="px-3 py-2 text-[#e8eaed]">
                              {row[header]}
                            </td>
                          ))}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>

                <label className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    checked={sendInvites}
                    onChange={e => setSendInvites(e.target.checked)}
                    className="rounded"
                    style={{ border: '1px solid rgba(255,255,255,0.08)' }}
                  />
                  <span className="text-sm text-[#e8eaed]">Send magic link invites immediately</span>
                </label>

                {!emailMapped && (
                  <p className="text-[12px] text-red-400">Map at least one column to Email before importing.</p>
                )}

                <div className="flex gap-3 justify-end pt-4">
                  <button
                    type="button"
                    onClick={() => setStep('idle')}
                    className="text-[#2ddbde] text-sm font-semibold px-4 py-2 rounded-lg hover:bg-[#353940]"
                    style={{ border: '1px solid #2ddbde' }}
                  >
                    Cancel
                  </button>
                  <button
                    type="button"
                    onClick={handleImport}
                    disabled={loading || !emailMapped}
                    className="btn-primary-gradient text-white text-sm font-semibold px-4 py-2 rounded-lg disabled:opacity-50"
                  >
                    {loading ? 'Importing…' : `Import ${parseResult.total_rows} Users`}
                  </button>
                </div>
              </>
            )}

            {/* STEP 3: DONE - Results */}
            {step === 'done' && result && (
              <>
                <h2 id="upload-modal-title" className="text-lg font-semibold text-[#e8eaed]">Import Complete</h2>

                <div className="space-y-3">
                  <div className="bg-emerald-500/15 rounded-lg p-3">
                    <div className="text-2xl font-bold text-emerald-400">{result.created}</div>
                    <div className="text-sm text-emerald-400 font-medium">Users Created</div>
                  </div>

                  {result.skipped > 0 && (
                    <div className="bg-[#31353c] rounded-lg p-3">
                      <div className="text-2xl font-bold text-[#9aa0a6]">{result.skipped}</div>
                      <div className="text-sm text-[#9aa0a6] font-medium">Users Skipped</div>
                    </div>
                  )}
                </div>

                <div className="flex gap-3 justify-end pt-4">
                  <button
                    type="button"
                    onClick={handleDone}
                    className="btn-primary-gradient text-white text-sm font-semibold px-4 py-2 rounded-lg"
                  >
                    Done
                  </button>
                </div>
              </>
            )}
          </div>
        </div>
      )}
    </>
  )
}

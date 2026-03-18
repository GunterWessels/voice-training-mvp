'use client'
import { useState } from 'react'
import { KBUploadTab } from '@/components/admin/KBUploadTab'
import { KBManageTab } from '@/components/admin/KBManageTab'

export default function KnowledgeBasePage() {
  const [tab, setTab] = useState<'upload' | 'manage'>('upload')
  const productId = 'tria_stents'

  return (
    <div className="max-w-5xl mx-auto p-6">
      <h1 className="text-xl font-semibold mb-6">Knowledge Base &mdash; {productId}</h1>
      <div className="border-b border-slate-700 mb-6">
        <div className="flex gap-0">
          {(['upload', 'manage'] as const).map(t => (
            <button key={t} onClick={() => setTab(t)}
              className={`px-5 py-2.5 text-sm font-medium border-b-2 transition-colors ${
                tab === t ? 'border-emerald-500 text-emerald-400'
                          : 'border-transparent text-slate-400 hover:text-slate-200'}`}>
              {t === 'upload' ? 'Upload Doc' : 'Manage Chunks'}
            </button>
          ))}
        </div>
      </div>
      {tab === 'upload' ? <KBUploadTab productId={productId} onIngested={() => setTab('manage')} />
                        : <KBManageTab productId={productId} />}
    </div>
  )
}

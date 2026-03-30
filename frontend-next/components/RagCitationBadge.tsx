'use client'
import { useState } from 'react'

export interface RagCitation {
  source_doc: string
  page?: number
  approved: boolean
}

interface Props {
  citation: RagCitation
}

export function RagCitationBadge({ citation }: Props) {
  const [showTooltip, setShowTooltip] = useState(false)
  const shortName = citation.source_doc.length > 18
    ? citation.source_doc.slice(0, 16) + '\u2026'
    : citation.source_doc
  const label = `[${shortName}${citation.page != null ? ` p.${citation.page}` : ''}]`

  return (
    <span className="relative inline-block">
      <span
        onMouseEnter={() => setShowTooltip(true)}
        onMouseLeave={() => setShowTooltip(false)}
        onFocus={() => setShowTooltip(true)}
        onBlur={() => setShowTooltip(false)}
        tabIndex={0}
        role="button"
        aria-label={`Source: ${citation.source_doc}${citation.page != null ? `, page ${citation.page}` : ''}${citation.approved ? '' : ' (unverified)'}`}
        className="font-mono text-[10px] ml-1 cursor-help"
        style={{ color: citation.approved ? 'rgba(45,219,222,0.7)' : 'rgba(251,191,36,0.7)' }}
      >
        {label}
      </span>

      {showTooltip && (
        <span
          className="absolute bottom-full left-0 mb-1.5 z-50 whitespace-nowrap rounded-lg px-2.5 py-1.5 text-[11px] pointer-events-none shadow-lg"
          style={{ background: '#31353c', border: '1px solid rgba(255,255,255,0.08)' }}
        >
          <span className="text-[#e8eaed]">{citation.source_doc}</span>
          {citation.page != null && <span className="text-[#9aa0a6]">{` \u00b7 p.${citation.page}`}</span>}
          {!citation.approved && (
            <span className="ml-1.5 text-[9px] font-bold uppercase tracking-wider" style={{ color: '#fbbf24' }}>
              Unverified
            </span>
          )}
        </span>
      )}
    </span>
  )
}

interface CitationListProps {
  citations: RagCitation[]
}

export function RagCitationList({ citations }: CitationListProps) {
  if (!citations || citations.length === 0) return null
  return (
    <span className="inline-flex flex-wrap gap-0.5">
      {citations.map((c, i) => (
        <RagCitationBadge key={i} citation={c} />
      ))}
    </span>
  )
}

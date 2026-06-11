import { memo, useMemo } from 'react'

interface Segment {
  text: string
  isHighlight: boolean
}

/**
 * Parse highlighted text and split into segments
 * Safely extracts text between <mark> tags without using dangerouslySetInnerHTML
 */
function parseHighlight(text: string): Segment[] {
  if (!text) return []

  const segments: Segment[] = []
  const markRegex = /<mark>(.*?)<\/mark>/gi

  let lastIndex = 0
  let match

  // Create a fresh regex for exec() iteration
  const regex = new RegExp(markRegex)

  while ((match = regex.exec(text)) !== null) {
    // Add text before this match
    if (match.index > lastIndex) {
      segments.push({
        text: text.slice(lastIndex, match.index),
        isHighlight: false
      })
    }

    // Add the highlighted text (content inside <mark> tags)
    segments.push({
      text: match[1],
      isHighlight: true
    })

    lastIndex = regex.lastIndex
  }

  // Add any remaining text after last match
  if (lastIndex < text.length) {
    segments.push({
      text: text.slice(lastIndex),
      isHighlight: false
    })
  }

  return segments
}

interface SearchHighlightProps {
  highlights?: Record<string, string>
  maxFields?: number
  className?: string
}

/**
 * SearchHighlight Component
 *
 * Renders search result highlights with matched terms marked.
 * Safely parses <mark> tags without using dangerouslySetInnerHTML.
 */
function SearchHighlight({ highlights, maxFields = 2, className = '' }: SearchHighlightProps) {
  // Get fields that have highlights, limited to maxFields
  const displayFields = useMemo(() => {
    if (!highlights || typeof highlights !== 'object') return []

    const entries = Object.entries(highlights)
      .filter(([, value]) => value && value.includes('<mark>'))
      .slice(0, maxFields)

    return entries.map(([field, text]) => ({
      field,
      segments: parseHighlight(text)
    }))
  }, [highlights, maxFields])

  if (displayFields.length === 0) {
    return null
  }

  return (
    <div className={`text-xs text-gray-600 mt-1 space-y-0.5 ${className}`}>
      {displayFields.map(({ field, segments }) => (
        <div key={field} className="truncate">
          <span className="text-gray-400 capitalize">{field}: </span>
          {segments.map((segment, idx) => (
            segment.isHighlight ? (
              <mark
                key={idx}
                className="bg-yellow-200 text-gray-900 px-0.5 rounded"
              >
                {segment.text}
              </mark>
            ) : (
              <span key={idx}>{segment.text}</span>
            )
          ))}
        </div>
      ))}
    </div>
  )
}

export default memo(SearchHighlight)

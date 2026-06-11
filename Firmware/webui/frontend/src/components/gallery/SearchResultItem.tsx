import { memo } from 'react'
import type { Photo } from '@/types/domain'
import PhotoGridItem from '../PhotoGridItem'
import SearchHighlight from './SearchHighlight'

/**
 * SearchResultItem Component
 *
 * Displays a search result with photo thumbnail and highlighted matched text.
 * Wraps PhotoGridItem with additional highlight display below the thumbnail.
 */

interface SearchResult {
  path: string
  filename: string
  highlights?: Record<string, string>
  metadata?: {
    date?: string
    [key: string]: unknown
  }
}

interface SearchResultItemProps {
  result: SearchResult
  onClick?: (photo: Photo) => void
  index?: number
  results?: SearchResult[]
}

function SearchResultItem({ result, onClick, index, results }: SearchResultItemProps) {
  // Convert result to photo format expected by PhotoGridItem
  const photo: Photo = {
    path: result.path,
    filename: result.filename,
    timestamp: result.metadata?.date || new Date().toISOString(),
    thumbnail_url: '',
    full_url: ''
  }

  return (
    <div className="flex flex-col">
      <PhotoGridItem
        photo={photo}
        onClick={onClick}
        index={index}
        photos={results}
      />
      {/* Show highlights below thumbnail */}
      {result.highlights && Object.keys(result.highlights).length > 0 && (
        <SearchHighlight
          highlights={result.highlights}
          maxFields={2}
          className="px-1"
        />
      )}
    </div>
  )
}

export default memo(SearchResultItem)

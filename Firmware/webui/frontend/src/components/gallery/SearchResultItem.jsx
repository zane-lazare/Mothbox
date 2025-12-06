import { memo } from 'react'
import PropTypes from 'prop-types'
import PhotoGridItem from '../PhotoGridItem'
import SearchHighlight from './SearchHighlight'

/**
 * SearchResultItem Component
 *
 * Displays a search result with photo thumbnail and highlighted matched text.
 * Wraps PhotoGridItem with additional highlight display below the thumbnail.
 *
 * @param {Object} props - Component props
 * @param {Object} props.result - Search result object from API
 * @param {string} props.result.path - Photo file path
 * @param {string} props.result.filename - Photo filename
 * @param {Object} [props.result.highlights] - Highlighted text for matched fields
 * @param {Object} [props.result.metadata] - Photo metadata
 * @param {Function} props.onClick - Click handler for viewing photo
 * @param {number} [props.index] - Result index in grid
 * @param {Array} [props.results] - All results array for range selection
 */
function SearchResultItem({ result, onClick, index, results }) {
  // Convert result to photo format expected by PhotoGridItem
  const photo = {
    path: result.path,
    filename: result.filename,
    date: result.metadata?.date || new Date().toISOString()
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

SearchResultItem.propTypes = {
  result: PropTypes.shape({
    path: PropTypes.string.isRequired,
    filename: PropTypes.string.isRequired,
    highlights: PropTypes.objectOf(PropTypes.string),
    metadata: PropTypes.object
  }).isRequired,
  onClick: PropTypes.func,
  index: PropTypes.number,
  results: PropTypes.array
}

export default memo(SearchResultItem)

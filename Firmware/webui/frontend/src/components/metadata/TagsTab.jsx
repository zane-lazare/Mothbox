import PropTypes from 'prop-types';
import MetadataField from './MetadataField';

/**
 * TagsTab Component
 *
 * Displays photo tags and annotations including user-defined tags,
 * species identification, and notes.
 *
 * Features:
 * - User tags rendered as blue badge pills
 * - Species identification field
 * - Notes field with preserved whitespace
 * - Read-only indicator (Phase 2)
 * - Empty state for no tags
 * - Section header
 *
 * @component
 * @example
 * const data = {
 *   user_tags: ['moth', 'nocturnal', 'large'],
 *   species: 'Luna Moth (Actias luna)',
 *   notes: 'Found near porch light.\nLarge wingspan.'
 * };
 * return <TagsTab data={data} />
 */
function TagsTab({ data }) {
  // Handle null or undefined data
  if (!data) {
    return (
      <div className="text-gray-500 text-sm">
        No tags data available
      </div>
    );
  }

  const { user_tags, species, notes } = data;

  // Check if we have any tags to display
  const hasTags = user_tags && user_tags.length > 0;

  return (
    <div className="space-y-4">
      {/* Section Header */}
      <div>
        <h3 className="text-sm font-medium text-gray-700 mb-2">Tags & Annotations</h3>
        <p className="text-xs text-gray-500 italic">
          Read-only (Tagging coming in Phase 3)
        </p>
      </div>

      {/* User Tags */}
      <div>
        <div className="text-xs font-medium text-gray-600 mb-2">Tags</div>
        {hasTags ? (
          <div className="flex flex-wrap gap-2">
            {user_tags.map((tag, index) => (
              <span
                key={index}
                className="bg-blue-100 text-blue-800 text-xs rounded-full px-2 py-1"
              >
                {tag}
              </span>
            ))}
          </div>
        ) : (
          <div className="text-gray-500 text-sm">
            No tags added yet (Tagging coming in Phase 3)
          </div>
        )}
      </div>

      {/* Species */}
      <MetadataField
        label="Species"
        value={species || null}
        copyable={false}
      />

      {/* Notes */}
      <div>
        <div className="text-xs font-medium text-gray-600 mb-1">Notes</div>
        {notes ? (
          <div className="text-sm text-gray-900 whitespace-pre-wrap">
            {notes}
          </div>
        ) : (
          <div className="text-sm text-gray-500">N/A</div>
        )}
      </div>
    </div>
  );
}

TagsTab.propTypes = {
  /**
   * Tags and annotations metadata object
   */
  data: PropTypes.shape({
    /** Array of user-defined tags */
    user_tags: PropTypes.arrayOf(PropTypes.string),
    /** Species identification */
    species: PropTypes.string,
    /** Multiline notes/observations */
    notes: PropTypes.string,
  }),
};

export default TagsTab;

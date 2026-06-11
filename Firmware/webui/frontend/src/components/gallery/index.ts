/**
 * Gallery Components - Photo gallery and bulk operations
 *
 * Components for displaying photo galleries, bulk actions, search, and photo context menus
 */

// Bulk operations
export { default as BulkActionsToolbar, type BulkActionsToolbarProps } from './BulkActionsToolbar'
export { default as BulkTagModal } from './BulkTagModal'
export { default as BulkSpeciesModal } from './BulkSpeciesModal'
export { default as BulkExportModal } from './BulkExportModal'
export { default as BulkDeleteConfirmModal } from './BulkDeleteConfirmModal'
export { default as BulkProgressModal } from './BulkProgressModal'

// Search components
export { default as SearchBar } from './SearchBar'
export { default as SearchHighlight } from './SearchHighlight'
export { default as SearchResultItem } from './SearchResultItem'
export { default as SearchHelp } from './SearchHelp'
export { default as AdvancedSearchBuilder } from './AdvancedSearchBuilder'

// Tagging components
export { default as QuickTagButton } from './QuickTagButton'
export { default as QuickTagDropdown } from './QuickTagDropdown'
export { default as TagAutocomplete } from './TagAutocomplete'
export { default as TagChip } from './TagChip'

// Gallery UI
export { default as SelectModeToggle } from './SelectModeToggle'
export { default as PhotoContextMenu } from './PhotoContextMenu'
export { default as GpsTagBanner } from './GpsTagBanner'

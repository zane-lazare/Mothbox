/**
 * Metadata Components - Photo metadata editing
 *
 * Components for viewing and editing photo EXIF, tags, species, notes, and custom fields
 */

// Main metadata panel
export { default as MetadataPanel } from './MetadataPanel'

// Metadata sections
export { default as MetadataTags } from './MetadataTags'
export { default as MetadataSpecies } from './MetadataSpecies'
export { default as MetadataNotes } from './MetadataNotes'
export { default as MetadataCustomFields } from './MetadataCustomFields'
export { default as MetadataEXIF } from './MetadataEXIF'

// Tabbed views
export { default as TagsTab } from './TagsTab'
export { default as DeploymentTab } from './DeploymentTab'
export { default as CameraTab } from './CameraTab'
export { default as CaptureTab } from './CaptureTab'

// UI components
export { default as AccordionSection } from './AccordionSection'
export { default as MetadataField } from './MetadataField'
export { default as SaveStatusIndicator } from './SaveStatusIndicator'
export { default as CopyButton } from './CopyButton'
export { default as MetadataSkeleton } from './MetadataSkeleton'

// Error handling
export { default as MetadataErrorBoundary } from './MetadataErrorBoundary'

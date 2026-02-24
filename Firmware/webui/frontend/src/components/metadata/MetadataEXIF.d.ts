/**
 * Type declarations for MetadataEXIF.jsx
 *
 * Provides TypeScript types during the gradual migration.
 */

interface MetadataEXIFProps {
  data: Record<string, unknown> | null | undefined
  disabled?: boolean
}

declare function MetadataEXIF(props: MetadataEXIFProps): JSX.Element
export default MetadataEXIF

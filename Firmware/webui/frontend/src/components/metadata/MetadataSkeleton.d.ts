/**
 * Type declarations for MetadataSkeleton.jsx
 *
 * Provides TypeScript types during the gradual migration.
 */

interface MetadataSkeletonProps {
  rows?: number
  className?: string
}

declare function MetadataSkeleton(props: MetadataSkeletonProps): JSX.Element
export default MetadataSkeleton

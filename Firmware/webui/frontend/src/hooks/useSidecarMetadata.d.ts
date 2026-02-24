/**
 * Type declarations for useSidecarMetadata.js
 *
 * Provides TypeScript types during the gradual migration.
 * IMPORTANT: Keep in sync with useSidecarMetadata.js.
 */

interface SidecarMetadata {
  tags?: string[]
  species?: string
  species_confidence?: string
  species_common_name?: string
  species_reference_url?: string
  notes?: string
  custom?: Record<string, string>
  [key: string]: unknown
}

interface UseSidecarMetadataResult {
  data: SidecarMetadata | undefined
  isLoading: boolean
  isError: boolean
  isSuccess: boolean
  error: Error | null
  updateTags: (tags: string[]) => void
  addTag: (tag: string) => void
  removeTag: (tag: string) => void
  updateSpecies: (species: string) => void
  updateNotes: (notes: string) => void
  updateMetadata: (updates: Partial<SidecarMetadata>) => Promise<unknown>
  isUpdating: boolean
  updateError: Error | null
}

declare function useSidecarMetadata(filename: string | null | undefined): UseSidecarMetadataResult
export default useSidecarMetadata

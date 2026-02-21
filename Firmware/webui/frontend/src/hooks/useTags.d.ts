/**
 * Type declarations for useTags.js
 *
 * Provides TypeScript types during the gradual migration.
 * IMPORTANT: Keep in sync with useTags.js.
 */

import { UseQueryResult } from '@tanstack/react-query'

interface TagData {
  name: string
  count: number
}

interface TagsResponse {
  tags: TagData[]
  total: number
}

interface UseTagsParams {
  sort?: string
  order?: string
  limit?: number
}

declare function useTags(params?: UseTagsParams): UseQueryResult<TagsResponse>
export default useTags

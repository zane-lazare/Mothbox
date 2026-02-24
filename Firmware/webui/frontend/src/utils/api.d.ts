/**
 * Type declarations for api.js
 *
 * Provides TypeScript types during the gradual migration.
 * Uses permissive types to support both production usage and vi.mock() in tests.
 */
import type { AxiosInstance } from 'axios'

export declare const api: AxiosInstance

export declare function getPhotoSidecarMetadata(
  filename: string
): Promise<{ data: Record<string, unknown> }>

export declare function updatePhotoSidecarMetadata(
  filename: string,
  updates: Record<string, unknown>
): Promise<{ data: Record<string, unknown> }>

export declare function getAllTags(
  params?: Record<string, unknown>
): Promise<{ data: Record<string, unknown> }>

export declare function getAllSpecies(
  params?: Record<string, unknown>
): Promise<{ data: Record<string, unknown> }>

export declare function searchPhotos(
  query: string,
  options?: { limit?: number; offset?: number }
): Promise<{ photos: unknown[]; total: number }>

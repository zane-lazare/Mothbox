import { useQuery, useMutation, useQueryClient, UseQueryResult, UseMutationResult } from '@tanstack/react-query'
import { QUERY_KEYS } from '../utils/queryKeys'
import {
  getGpsExifStatus,
  getGpsExifConfig,
  updateGpsExifConfig,
  batchTagPhotos,
  tagSinglePhoto,
} from '../utils/api'

interface GpsExifStatus {
  enabled: boolean
  [key: string]: unknown
}

interface GpsExifConfig {
  enabled: boolean
  [key: string]: unknown
}

interface BatchTagData {
  photo_paths: string[]
  [key: string]: unknown
}

interface SingleTagData {
  photo_path: string
  [key: string]: unknown
}

export function useGpsExifStatus(): UseQueryResult<GpsExifStatus, Error> {
  return useQuery({
    queryKey: QUERY_KEYS.GPS_EXIF_STATUS,
    queryFn: async () => {
      const response = await getGpsExifStatus()
      return response.data
    },
    staleTime: 10 * 1000,
  })
}

export function useGpsExifConfig(): UseQueryResult<GpsExifConfig, Error> {
  return useQuery({
    queryKey: QUERY_KEYS.GPS_EXIF_CONFIG,
    queryFn: async () => {
      const response = await getGpsExifConfig()
      return response.data
    },
    staleTime: 60 * 1000,
  })
}

export function useUpdateGpsExifConfig(): UseMutationResult<unknown, Error, Partial<GpsExifConfig>> {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (config: Partial<GpsExifConfig>) => updateGpsExifConfig(config),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.GPS_EXIF_CONFIG })
    },
  })
}

export function useBatchTagPhotos(): UseMutationResult<unknown, Error, BatchTagData> {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (data: BatchTagData) => batchTagPhotos(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.GPS_EXIF_STATUS })
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.PHOTOS })
    },
  })
}

export function useTagSinglePhoto(): UseMutationResult<unknown, Error, SingleTagData> {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (data: SingleTagData) => tagSinglePhoto(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.GPS_EXIF_STATUS })
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.PHOTOS })
    },
  })
}

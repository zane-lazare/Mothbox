import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { QUERY_KEYS } from '../utils/queryKeys'
import {
  getGpsExifStatus,
  getGpsExifConfig,
  updateGpsExifConfig,
  batchTagPhotos,
  tagSinglePhoto,
} from '../utils/api'

export function useGpsExifStatus() {
  return useQuery({
    queryKey: QUERY_KEYS.GPS_EXIF_STATUS,
    queryFn: async () => {
      const response = await getGpsExifStatus()
      return response.data
    },
    staleTime: 10 * 1000,
  })
}

export function useGpsExifConfig() {
  return useQuery({
    queryKey: QUERY_KEYS.GPS_EXIF_CONFIG,
    queryFn: async () => {
      const response = await getGpsExifConfig()
      return response.data
    },
    staleTime: 60 * 1000,
  })
}

export function useUpdateGpsExifConfig() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (config) => updateGpsExifConfig(config),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.GPS_EXIF_CONFIG })
    },
  })
}

export function useBatchTagPhotos() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (data) => batchTagPhotos(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.GPS_EXIF_STATUS })
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.PHOTOS })
    },
  })
}

export function useTagSinglePhoto() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (data) => tagSinglePhoto(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.GPS_EXIF_STATUS })
    },
  })
}

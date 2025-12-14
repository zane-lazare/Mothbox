/**
 * React Query hooks for Deployment Metadata (Issue #125, Subtask 3)
 *
 * Provides hooks for managing deployment metadata CRUD operations:
 * - useDeployments: List all deployments
 * - useDeployment: Get single deployment
 * - useCreateDeployment: Create new deployment
 * - useUpdateDeployment: Update existing deployment
 * - useDeleteDeployment: Delete deployment
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { QUERY_KEYS } from '../utils/queryKeys'
import {
  listDeployments,
  getDeployment,
  createDeployment,
  updateDeployment,
  deleteDeployment,
} from '../utils/deploymentApi'

/**
 * List all deployments
 *
 * @returns {Object} React Query result
 * @returns {Object} data - { deployments: [...], total }
 * @returns {boolean} isLoading - Whether initial query is loading
 * @returns {boolean} isError - Whether an error occurred
 * @returns {Object} error - Error object if query failed
 *
 * @example
 * const { data, isLoading } = useDeployments()
 * if (data) {
 *   console.log(`${data.total} deployments`)
 *   data.deployments.forEach(d => console.log(d.name))
 * }
 */
export function useDeployments() {
  return useQuery({
    queryKey: QUERY_KEYS.DEPLOYMENTS,
    queryFn: async () => {
      const response = await listDeployments()
      return response.data
    },
    staleTime: 5 * 60 * 1000, // 5 minutes - deployments change infrequently
  })
}

/**
 * Get single deployment by directory path
 *
 * @param {string|null} directory - Directory path (null to disable query)
 * @returns {Object} React Query result
 * @returns {Object} data - Deployment metadata
 * @returns {boolean} isLoading - Whether initial query is loading
 * @returns {boolean} isError - Whether an error occurred
 * @returns {Object} error - Error object if query failed
 *
 * @example
 * const { data, isLoading } = useDeployment('/photos/deployment1')
 * if (data) {
 *   console.log(`Deployment: ${data.deployment_name}`)
 *   console.log(`Location: ${data.location_name}`)
 * }
 */
export function useDeployment(directory) {
  return useQuery({
    queryKey: QUERY_KEYS.DEPLOYMENT(directory),
    queryFn: async () => {
      const response = await getDeployment(directory)
      return response.data
    },
    enabled: !!directory, // Disable query if directory is null/undefined
    staleTime: 5 * 60 * 1000, // 5 minutes
  })
}

/**
 * Create new deployment mutation
 *
 * Invalidates deployments list cache on success.
 *
 * @returns {Object} React Query mutation result
 * @returns {Function} mutate - Mutation function (fire and forget)
 * @returns {Function} mutateAsync - Async mutation function (returns promise)
 * @returns {boolean} isPending - Whether mutation is in progress
 * @returns {boolean} isError - Whether mutation failed
 * @returns {Object} error - Error object if mutation failed
 * @returns {Object} data - Response data on success
 *
 * @example
 * const { mutate, isPending } = useCreateDeployment()
 *
 * const handleCreate = () => {
 *   mutate({
 *     directory: '/photos/new-deployment',
 *     data: {
 *       deployment_name: 'Oak Ridge Survey',
 *       location_name: 'Oak Ridge, TN'
 *     }
 *   }, {
 *     onSuccess: (response) => {
 *       console.log('Created:', response.data.directory)
 *     },
 *     onError: (error) => {
 *       console.error('Failed:', error.message)
 *     }
 *   })
 * }
 */
export function useCreateDeployment() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ directory, data }) => createDeployment(directory, data),
    onSuccess: () => {
      // Invalidate deployments list to show new deployment
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.DEPLOYMENTS })
    },
  })
}

/**
 * Update deployment mutation
 *
 * Invalidates deployment cache and deployments list on success.
 *
 * @returns {Object} React Query mutation result
 * @returns {Function} mutate - Mutation function with { directory, data } parameter
 * @returns {Function} mutateAsync - Async mutation function
 * @returns {boolean} isPending - Whether mutation is in progress
 * @returns {boolean} isError - Whether mutation failed
 * @returns {Object} error - Error object if mutation failed
 * @returns {Object} data - Response data on success
 *
 * @example
 * const { mutate, isPending } = useUpdateDeployment()
 *
 * const handleUpdate = (directory) => {
 *   mutate({
 *     directory,
 *     data: { end_date: '2024-12-31' }
 *   }, {
 *     onSuccess: () => {
 *       console.log('Updated')
 *     }
 *   })
 * }
 */
export function useUpdateDeployment() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ directory, data }) => updateDeployment(directory, data),
    onSuccess: (response, { directory }) => {
      // Invalidate specific deployment to update immediately
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.DEPLOYMENT(directory) })
      // Invalidate deployments list to update names/counts
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.DEPLOYMENTS })
    },
  })
}

/**
 * Delete deployment mutation
 *
 * Invalidates deployment cache and deployments list on success.
 *
 * @returns {Object} React Query mutation result
 * @returns {Function} mutate - Mutation function with directory parameter
 * @returns {Function} mutateAsync - Async mutation function
 * @returns {boolean} isPending - Whether mutation is in progress
 * @returns {boolean} isError - Whether mutation failed
 * @returns {Object} error - Error object if mutation failed
 * @returns {Object} data - Response data on success
 *
 * @example
 * const { mutate, isPending } = useDeleteDeployment()
 *
 * const handleDelete = (directory) => {
 *   if (confirm('Delete this deployment?')) {
 *     mutate(directory, {
 *       onSuccess: () => {
 *         console.log('Deleted')
 *       }
 *     })
 *   }
 * }
 */
export function useDeleteDeployment() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (directory) => deleteDeployment(directory),
    onSuccess: (response, directory) => {
      // Invalidate specific deployment cache
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.DEPLOYMENT(directory) })
      // Invalidate deployments list
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.DEPLOYMENTS })
    },
  })
}

export default useDeployments

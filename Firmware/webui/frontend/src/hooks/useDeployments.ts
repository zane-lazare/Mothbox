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

import { useQuery, useMutation, useQueryClient, UseQueryResult, UseMutationResult } from '@tanstack/react-query'
import { QUERY_KEYS } from '../utils/queryKeys'
import {
  listDeployments,
  getDeployment,
  createDeployment,
  updateDeployment,
  deleteDeployment,
} from '../utils/deploymentApi'
import type { DeploymentMetadata } from '../types'

interface DeploymentListItem {
  directory: string
  deployment_name?: string
  location_name?: string
  photo_count: number
}

interface DeploymentsData {
  deployments: DeploymentListItem[]
  total: number
}

interface CreateDeploymentParams {
  directory: string
  data: Partial<DeploymentMetadata>
}

interface UpdateDeploymentParams {
  directory: string
  data: Partial<DeploymentMetadata>
}

/**
 * List all deployments
 *
 * @returns React Query result
 *
 * @example
 * const { data, isLoading } = useDeployments()
 * if (data) {
 *   console.log(`${data.total} deployments`)
 *   data.deployments.forEach(d => console.log(d.name))
 * }
 */
export function useDeployments(): UseQueryResult<DeploymentsData, Error> {
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
 * @param directory - Directory path (null to disable query)
 * @returns React Query result
 *
 * @example
 * const { data, isLoading } = useDeployment('/photos/deployment1')
 * if (data) {
 *   console.log(`Deployment: ${data.deployment_name}`)
 *   console.log(`Location: ${data.location_name}`)
 * }
 */
export function useDeployment(directory: string | null): UseQueryResult<DeploymentMetadata, Error> {
  return useQuery({
    queryKey: QUERY_KEYS.DEPLOYMENT(directory!),
    queryFn: async () => {
      const response = await getDeployment(directory!)
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
 * @returns React Query mutation result
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
export function useCreateDeployment(): UseMutationResult<unknown, Error, CreateDeploymentParams> {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ directory, data }: CreateDeploymentParams) => createDeployment(directory, data),
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
 * @returns React Query mutation result
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
export function useUpdateDeployment(): UseMutationResult<unknown, Error, UpdateDeploymentParams> {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ directory, data }: UpdateDeploymentParams) => updateDeployment(directory, data),
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
 * @returns React Query mutation result
 *
 * @example
 * const { mutate, isPending } = useDeleteDeployment()
 * const [showConfirm, setShowConfirm] = useState(false)
 * const [directoryToDelete, setDirectoryToDelete] = useState(null)
 *
 * const handleDeleteClick = (directory) => {
 *   setDirectoryToDelete(directory)
 *   setShowConfirm(true)
 * }
 *
 * const handleConfirmDelete = () => {
 *   mutate(directoryToDelete, {
 *     onSuccess: () => setShowConfirm(false)
 *   })
 * }
 *
 * <ConfirmDialog
 *   isOpen={showConfirm}
 *   onClose={() => setShowConfirm(false)}
 *   onConfirm={handleConfirmDelete}
 *   title="Delete Deployment?"
 *   message="This action cannot be undone."
 *   confirmLabel="Delete"
 *   variant="danger"
 *   isLoading={isPending}
 * />
 */
export function useDeleteDeployment(): UseMutationResult<unknown, Error, string> {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (directory: string) => deleteDeployment(directory),
    onSuccess: (response, directory) => {
      // Invalidate specific deployment cache
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.DEPLOYMENT(directory) })
      // Invalidate deployments list
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.DEPLOYMENTS })
    },
  })
}

export default useDeployments

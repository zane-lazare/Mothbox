import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { getGpioStatus, getGpioHealth, controlGpio, triggerFlash } from '../utils/api'
import { QUERY_KEYS } from '../utils/queryKeys'

/**
 * GPIO status interface representing relay states
 */
interface GpioStatus {
  Relay_Ch1?: boolean
  Relay_Ch2?: boolean
  Relay_Ch3?: boolean
  error?: string
}

/**
 * Health data interface for daemon status
 */
interface HealthData {
  reachable: boolean
  uptime_seconds?: number | null
}

/**
 * Control mutation parameters
 */
interface ControlMutationParams {
  relay: string
  state: boolean
}

/**
 * Context returned from optimistic update
 */
interface MutationContext {
  previousStatus?: GpioStatus
}

/**
 * Format uptime seconds into human-readable string
 * @param seconds - Uptime in seconds
 * @returns Formatted uptime string (e.g., "2d 5h", "3h 15m", "45m")
 */
function formatUptime(seconds: number | null | undefined): string {
  if (seconds == null || seconds < 0) return ''
  const days = Math.floor(seconds / 86400)
  const hours = Math.floor((seconds % 86400) / 3600)
  const minutes = Math.floor((seconds % 3600) / 60)
  if (days > 0) return `${days}d ${hours}h`
  if (hours > 0) return `${hours}h ${minutes}m`
  return `${minutes}m`
}

export default function GPIO(): React.JSX.Element {
  const queryClient = useQueryClient()

  const { data: gpioStatus, isLoading } = useQuery<GpioStatus>({
    queryKey: QUERY_KEYS.GPIO_STATUS,
    queryFn: () => getGpioStatus().then(res => res.data),
    refetchInterval: 5000, // Refresh every 5 seconds instead of 2
    refetchOnWindowFocus: false, // Don't refetch when window regains focus
    staleTime: 2000, // Consider data fresh for 2 seconds
  })

  const { data: healthData, isError: isHealthError } = useQuery<HealthData>({
    queryKey: QUERY_KEYS.GPIO_HEALTH,
    queryFn: () => getGpioHealth().then(res => res.data),
    refetchInterval: 10000,
    refetchOnWindowFocus: false,
    staleTime: 5000,
    retry: 1,
  })

  const daemonOnline = healthData?.reachable === true && !isHealthError

  const controlMutation = useMutation<unknown, Error, ControlMutationParams, MutationContext>({
    mutationFn: ({ relay, state }: ControlMutationParams) => controlGpio(relay, state),
    onMutate: async ({ relay, state }: ControlMutationParams) => {
      // Cancel any outgoing refetches
      await queryClient.cancelQueries({ queryKey: QUERY_KEYS.GPIO_STATUS })

      // Snapshot the previous value
      const previousStatus = queryClient.getQueryData<GpioStatus>(QUERY_KEYS.GPIO_STATUS)

      // Optimistically update to the new value
      queryClient.setQueryData<GpioStatus>(QUERY_KEYS.GPIO_STATUS, (old) => ({
        ...old,
        [relay]: state
      }))

      return { previousStatus }
    },
    onError: (_err: Error, _variables: ControlMutationParams, context: MutationContext | undefined) => {
      // Rollback on error
      if (context?.previousStatus) {
        queryClient.setQueryData(QUERY_KEYS.GPIO_STATUS, context.previousStatus)
      }
    },
    onSettled: () => {
      // Refetch after mutation
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.GPIO_STATUS })
    },
  })

  const flashMutation = useMutation<unknown, Error>({
    mutationFn: triggerFlash,
  })

  const handleToggle = (relay: string, currentState: boolean | undefined): void => {
    controlMutation.mutate({ relay, state: !currentState })
  }

  const handleFlash = (): void => {
    flashMutation.mutate()
  }

  // Only show loading on initial load, not on background refetches
  if (isLoading && !gpioStatus) {
    return <div className="text-center py-12">Loading GPIO status...</div>
  }

  if (gpioStatus?.error) {
    return (
      <div className="text-center py-12">
        <p className="text-red-600">{gpioStatus.error}</p>
        <p className="text-sm text-gray-500 mt-2">GPIO may not be available in this environment</p>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-bold text-gray-900">GPIO Controls</h2>

      {/* Daemon Health */}
      <div className="flex items-center gap-2 text-sm text-gray-700">
        <span
          className={`inline-block h-2.5 w-2.5 rounded-full ${daemonOnline ? 'bg-green-500' : 'bg-red-500'}`}
          aria-hidden="true"
        />
        {daemonOnline ? (
          <span>
            Daemon connected
            {healthData?.uptime_seconds != null && (
              <span className="text-gray-500"> &mdash; uptime {formatUptime(healthData.uptime_seconds)}</span>
            )}
          </span>
        ) : (
          <span className="text-red-600">Daemon offline</span>
        )}
      </div>

      {/* Relay Controls */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {/* Relay Ch1 - Attract Lights */}
        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-lg font-semibold mb-4">Attract Lights</h3>
          <p className="text-sm text-gray-600 mb-4">Relay Ch1</p>
          <button
            onClick={() => handleToggle('Relay_Ch1', gpioStatus?.Relay_Ch1)}
            className={`w-full py-3 rounded-lg font-semibold transition-colors ${
              gpioStatus?.Relay_Ch1
                ? 'bg-green-600 text-white hover:bg-green-700'
                : 'bg-gray-300 text-gray-700 hover:bg-gray-400'
            }`}
          >
            {gpioStatus?.Relay_Ch1 ? 'ON' : 'OFF'}
          </button>
        </div>

        {/* Relay Ch2 - Flash */}
        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-lg font-semibold mb-4">Photo Flash</h3>
          <p className="text-sm text-gray-600 mb-4">Relay Ch2</p>
          <div className="space-y-2">
            <button
              onClick={() => handleToggle('Relay_Ch2', gpioStatus?.Relay_Ch2)}
              className={`w-full py-3 rounded-lg font-semibold transition-colors ${
                gpioStatus?.Relay_Ch2
                  ? 'bg-green-600 text-white hover:bg-green-700'
                  : 'bg-gray-300 text-gray-700 hover:bg-gray-400'
              }`}
            >
              {gpioStatus?.Relay_Ch2 ? 'ON' : 'OFF'}
            </button>
            <button
              onClick={handleFlash}
              disabled={flashMutation.isPending}
              className="w-full py-2 bg-yellow-500 text-white rounded-lg hover:bg-yellow-600 disabled:bg-gray-400"
            >
              {flashMutation.isPending ? 'Flashing...' : 'Trigger Flash (100ms)'}
            </button>
          </div>
        </div>

        {/* Relay Ch3 - UV */}
        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-lg font-semibold mb-4">UV Light</h3>
          <p className="text-sm text-gray-600 mb-4">Relay Ch3</p>
          <button
            onClick={() => handleToggle('Relay_Ch3', gpioStatus?.Relay_Ch3)}
            className={`w-full py-3 rounded-lg font-semibold transition-colors ${
              gpioStatus?.Relay_Ch3
                ? 'bg-green-600 text-white hover:bg-green-700'
                : 'bg-gray-300 text-gray-700 hover:bg-gray-400'
            }`}
          >
            {gpioStatus?.Relay_Ch3 ? 'ON' : 'OFF'}
          </button>
        </div>
      </div>

      {/* Status Info */}
      <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
        <p className="text-sm text-blue-800">
          <strong>Note:</strong> GPIO controls interact directly with the Mothbox hardware.
          Changes are applied immediately.
        </p>
      </div>
    </div>
  )
}

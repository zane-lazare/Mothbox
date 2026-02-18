import { useSocketContext } from '../contexts/SocketContext'

/**
 * useSocket - Thin wrapper around SocketContext (#368)
 *
 * Returns the shared Socket.io connection and connection status.
 * Throws if used outside of a SocketProvider.
 *
 * @returns {{ socket: import('socket.io-client').Socket | null, connected: boolean }}
 *
 * @example
 * const { socket, connected } = useSocket()
 *
 * useEffect(() => {
 *   if (!socket) return
 *   const handler = (data) => { ... }
 *   socket.on('event_name', handler)
 *   return () => socket.off('event_name', handler)
 * }, [socket])
 */
export default function useSocket() {
  const context = useSocketContext()
  if (context === null) {
    throw new Error('useSocket must be used within a SocketProvider')
  }
  return context
}

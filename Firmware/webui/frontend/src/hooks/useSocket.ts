import { useSocketContext } from '../contexts/SocketContext'
import type { Socket } from 'socket.io-client'

export interface UseSocketResult {
  socket: Socket | null
  connected: boolean
  reconnecting: boolean
}

/**
 * useSocket - Thin wrapper around SocketContext (#368)
 *
 * Returns the shared Socket.io connection and connection status.
 * Throws if used outside of a SocketProvider.
 *
 * @returns Socket connection and status
 *
 * @example
 * const { socket, connected, reconnecting } = useSocket()
 *
 * useEffect(() => {
 *   if (!socket) return
 *   const handler = (data) => { ... }
 *   socket.on('event_name', handler)
 *   return () => socket.off('event_name', handler)
 * }, [socket])
 */
export default function useSocket(): UseSocketResult {
  const context = useSocketContext()
  if (context === null) {
    throw new Error('useSocket must be used within a SocketProvider')
  }
  return context
}

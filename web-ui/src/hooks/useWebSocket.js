import { useEffect, useRef, useCallback } from 'react'
import { useSimulationStore } from '../store/useSimulationStore'

export function useWebSocket(url = 'ws://localhost:8765') {
  const wsRef = useRef(null)
  const reconnectTimeoutRef = useRef(null)
  const { updateFromMessage, setConnected } = useSimulationStore()

  const connect = useCallback(() => {
    if (wsRef.current && (wsRef.current.readyState === WebSocket.OPEN || wsRef.current.readyState === WebSocket.CONNECTING)) {
      return
    }

    try {
      const ws = new WebSocket(url)
      wsRef.current = ws

      ws.onopen = () => {
        console.log('[WebSocket] Connected to simulation backend:', url)
        setConnected(true)
      }

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data)
          if (data && data.type === 'simulation_data') {
            updateFromMessage(data)
          }
        } catch (e) {
          console.error('[WebSocket] Error parsing message:', e)
        }
      }

      ws.onclose = () => {
        setConnected(false)
        wsRef.current = null
        reconnectTimeoutRef.current = setTimeout(connect, 600)
      }

      ws.onerror = (err) => {
        ws.close()
      }
    } catch (err) {
      reconnectTimeoutRef.current = setTimeout(connect, 600)
    }
  }, [url, updateFromMessage, setConnected])

  const disconnect = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current)
    }
    if (wsRef.current) {
      wsRef.current.close()
      wsRef.current = null
    }
    setConnected(false)
  }, [setConnected])

  useEffect(() => {
    connect()
    return () => disconnect()
  }, [connect, disconnect])

  return { connect, disconnect }
}
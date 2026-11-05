'use client'

import { useCallback, useEffect, useRef, useState } from 'react'
import apiClient from '@/lib/api-client'

interface Options {
  enabled?: boolean
  onNewSale?: (data: Record<string, unknown>) => void
  onNewOrder?: (data: Record<string, unknown>) => void
  onTableReady?: (data: Record<string, unknown>) => void
  onError?: (message: string) => void
  autoReconnect?: boolean
  reconnectDelay?: number
}
interface Toast { id: string; message: string; type: 'success' | 'info' | 'error' }
const toasts = new Map<string, Toast>()
const subscribers = new Set<() => void>()
export function showToast(message: string, type: Toast['type'] = 'info', duration = 3000) {
  const id = globalThis.crypto?.randomUUID?.() ?? `toast-${Date.now()}-${Math.random()}`
  toasts.set(id, { id, message, type })
  subscribers.forEach(callback => callback())
  if (duration > 0) setTimeout(() => dismissToast(id), duration)
  return id
}
export function onToastChange(callback: () => void) { subscribers.add(callback); return () => { subscribers.delete(callback) } }
export function getActiveToasts() { return Array.from(toasts.values()) }
export function dismissToast(id: string) { toasts.delete(id); subscribers.forEach(callback => callback()) }

function record(value: unknown): value is Record<string, unknown> { return typeof value === 'object' && value !== null && !Array.isArray(value) }

function playDing() {
  try {
    const audio = new AudioContext()
    const oscillator = audio.createOscillator()
    const gain = audio.createGain()
    oscillator.connect(gain); gain.connect(audio.destination)
    oscillator.frequency.value = 800
    gain.gain.setValueAtTime(0.15, audio.currentTime)
    gain.gain.exponentialRampToValueAtTime(0.001, audio.currentTime + 0.1)
    oscillator.onended = () => { void audio.close() }
    oscillator.start(); oscillator.stop(audio.currentTime + 0.1)
  } catch { /* Notifications still work when audio is unavailable. */ }
}

export function useWebSocket(options: Options = {}) {
  const { enabled = true, autoReconnect = true, reconnectDelay = 1000 } = options
  const callbacks = useRef(options)
  useEffect(() => { callbacks.current = options }, [options])
  const controls = useRef<{ connect: () => void; disconnect: () => void } | null>(null)
  const [isConnected, setConnected] = useState(false)

  useEffect(() => {
    if (!enabled) return
    let stopped = false
    let socket: WebSocket | null = null
    let retry: ReturnType<typeof setTimeout> | undefined
    let heartbeat: ReturnType<typeof setInterval> | undefined
    let attempts = 0
    let lastPong = 0
    let connecting = false
    const clearHeartbeat = () => { clearInterval(heartbeat); heartbeat = undefined }

    function schedule() {
      if (stopped || !autoReconnect || attempts >= 6) return
      const delay = Math.min(reconnectDelay * 2 ** attempts++, 30000) + Math.random() * 300
      clearTimeout(retry)
      retry = setTimeout(() => { void open() }, delay)
    }

    async function open() {
      if (stopped || connecting || (socket && socket.readyState < WebSocket.CLOSING)) return
      if (!localStorage.getItem('access_token')) return
      connecting = true
      try {
        // Refresh expired credentials through the existing HTTP interceptor.
        await apiClient.get('/auth/me')
        const token = localStorage.getItem('access_token')
        if (stopped || !token) return
        const base = new URL(apiClient.defaults.baseURL || 'http://localhost:8000/api/v1', window.location.origin)
        base.pathname = `${base.pathname.replace(/\/$/, '')}/ws`
        base.protocol = base.protocol === 'https:' ? 'wss:' : 'ws:'
        base.search = ''; base.hash = ''
        const ws = new WebSocket(base.toString())
        socket = ws
        ws.onopen = () => { if (!stopped) ws.send(JSON.stringify({ event: 'AUTH', token })) }
        ws.onmessage = event => {
          if (stopped || socket !== ws) return
          let message: unknown
          try { message = JSON.parse(event.data) } catch { return }
          if (!record(message) || !record(message.data) || typeof message.event !== 'string') return
          const data = message.data
          if (message.event === 'CONNECTED') {
            attempts = 0; lastPong = Date.now(); setConnected(true)
            clearHeartbeat()
            heartbeat = setInterval(() => {
              if (Date.now() - lastPong > 45000) { ws.close(); return }
              if (ws.readyState === WebSocket.OPEN) ws.send('ping')
            }, 15000)
          } else if (message.event === 'PONG') lastPong = Date.now()
          else if (message.event === 'NEW_SALE' && typeof data.amount === 'number' && Number.isFinite(data.amount) &&
                   typeof data.item_count === 'number' && Number.isInteger(data.item_count)) {
            showToast(`New Sale: ₹${data.amount.toFixed(2)} (${data.item_count} items)`, 'success')
            playDing()
            callbacks.current.onNewSale?.(data)
          } else if (message.event === 'NEW_ORDER' && typeof data.order_id === 'string' && (typeof data.table === 'string' || typeof data.table === 'number')) {
            showToast(`New Order #${data.order_id} for Table ${data.table}`)
            callbacks.current.onNewOrder?.(data)
          } else if (message.event === 'TABLE_READY' && (typeof data.table === 'string' || typeof data.table === 'number')) {
            showToast(`Table ${data.table} is ready`)
            callbacks.current.onTableReady?.(data)
          } else if (message.event === 'SYSTEM_EVENT' && typeof data.message === 'string') showToast(data.message)
        }
        ws.onerror = () => { if (!stopped) callbacks.current.onError?.('Realtime connection unavailable') }
        ws.onclose = event => {
          if (stopped || socket !== ws) return
          socket = null; connecting = false; clearHeartbeat(); setConnected(false)
          if (event.code !== 1008 && event.code !== 1009) schedule()
        }
      } catch {
        if (!stopped) { callbacks.current.onError?.('Realtime connection unavailable'); schedule() }
      } finally { connecting = false }
    }

    function disconnect() {
      stopped = true; clearTimeout(retry); clearHeartbeat()
      socket?.close(); socket = null; setConnected(false)
    }
    controls.current = { connect: () => { stopped = false; attempts = 0; void open() }, disconnect }
    void open()
    return () => { stopped = true; clearTimeout(retry); clearHeartbeat(); socket?.close(); controls.current = null }
  }, [enabled, autoReconnect, reconnectDelay])

  const connect = useCallback(() => controls.current?.connect(), [])
  const disconnect = useCallback(() => controls.current?.disconnect(), [])
  return { isConnected: enabled && isConnected, connect, disconnect }
}

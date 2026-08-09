/**
 * useWebSocket Hook - Real-time Event Listener
 * 
 * Connects to the backend WebSocket at /ws endpoint for real-time event notifications.
 * Features:
 * - JWT authentication via query params
 * - Multi-tenant isolation (events scoped to user's tenant)
 * - Event type handling (NEW_SALE, NEW_ORDER, TABLE_READY, etc.)
 * - Toast notifications with Rupee amounts
 * - Audio alerts ("ding" sound)
 * - Automatic reconnection on disconnect
 * - Error handling and logging
 */

import { useEffect, useRef, useCallback } from 'react';

interface WebSocketEvent {
  event: string;
  data: Record<string, unknown>;
  timestamp?: string;
}

interface UseWebSocketOptions {
  onNewSale?: (data: Record<string, unknown>) => void;
  onNewOrder?: (data: Record<string, unknown>) => void;
  onTableReady?: (data: Record<string, unknown>) => void;
  onError?: (error: string) => void;
  autoReconnect?: boolean;
  reconnectDelay?: number;
}

interface Toast {
  id: string;
  message: string;
  type: 'success' | 'info' | 'error';
}

// Global toast state (simple in-memory storage)
const toastStore = new Map<string, Toast>();
const toastCallbacks = new Set<() => void>();

/**
 * Show a toast notification
 * @param message Toast message to display
 * @param type Toast type (success, info, error)
 * @param duration Auto-dismiss after duration (ms)
 */
export function showToast(message: string, type: 'success' | 'info' | 'error' = 'info', duration: number = 3000) {
  const id = `toast-${Date.now()}-${Math.random()}`;
  const toast: Toast = { id, message, type };
  
  toastStore.set(id, toast);
  
  // Notify listeners
  toastCallbacks.forEach(cb => cb());
  
  // Auto-remove after duration
  if (duration > 0) {
    setTimeout(() => {
      toastStore.delete(id);
      toastCallbacks.forEach(cb => cb());
    }, duration);
  }
  
  return id;
}

/**
 * Subscribe to toast changes
 */
export function onToastChange(callback: () => void) {
  toastCallbacks.add(callback);
  return () => {
    toastCallbacks.delete(callback);
  };
}

/**
 * Get all active toasts
 */
export function getActiveToasts(): Toast[] {
  return Array.from(toastStore.values());
}

/**
 * Play a "ding" sound notification
 * Uses Web Audio API to generate a simple beep tone
 */
function playDingSound() {
  try {
    // Create audio context
    const AudioContext = window.AudioContext || (window as any).webkitAudioContext;
    if (!AudioContext) return;
    
    const audioContext = new AudioContext();
    const now = audioContext.currentTime;
    
    // Create a simple ding: short beep at 800Hz
    const oscillator = audioContext.createOscillator();
    const envelope = audioContext.createGain();
    
    oscillator.connect(envelope);
    envelope.connect(audioContext.destination);
    
    oscillator.frequency.value = 800; // Hz
    oscillator.type = 'sine';
    
    // Quick attack, quick decay (telegraph-style ding)
    envelope.gain.setValueAtTime(0.3, now);
    envelope.gain.exponentialRampToValueAtTime(0.01, now + 0.1);
    
    oscillator.start(now);
    oscillator.stop(now + 0.1);
  } catch (error) {
    console.debug('Audio notification disabled or not supported');
  }
}

/**
 * Main WebSocket hook for real-time event handling
 */
export function useWebSocket(options: UseWebSocketOptions = {}) {
  const {
    onNewSale,
    onNewOrder,
    onTableReady,
    onError,
    autoReconnect = true,
    reconnectDelay = 3000,
  } = options;
  
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const isConnectingRef = useRef(false);
  
  /**
   * Extract JWT token from localStorage
   */
  const getToken = useCallback(() => {
    try {
      return localStorage.getItem('access_token') || '';
    } catch {
      return '';
    }
  }, []);
  
  /**
   * Connect to WebSocket endpoint
   */
  const connect = useCallback(() => {
    if (isConnectingRef.current || wsRef.current?.readyState === WebSocket.OPEN) {
      return;
    }
    
    isConnectingRef.current = true;
    const token = getToken();
    
    if (!token) {
      console.warn('WebSocket: No authentication token available');
      isConnectingRef.current = false;
      return;
    }
    
    try {
      const protocol = window.location.protocol === 'https:' ? 'wss' : 'ws';
      const wsUrl = `${protocol}://${window.location.host}/api/v1/ws?token=${encodeURIComponent(token)}`;
      
      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;
      
      ws.onopen = () => {
        console.log('WebSocket connected');
        isConnectingRef.current = false;
        
        // Clear any pending reconnection timeouts
        if (reconnectTimeoutRef.current) {
          clearTimeout(reconnectTimeoutRef.current);
          reconnectTimeoutRef.current = null;
        }
      };
      
      ws.onmessage = (event) => {
        try {
          const message = JSON.parse(event.data) as WebSocketEvent;
          console.debug('WebSocket message received:', message.event);
          
          // Handle different event types
          switch (message.event) {
            case 'NEW_SALE': {
              const amount = message.data.amount as number;
              const itemCount = message.data.item_count as number;
              
              // Play notification sound
              playDingSound();
              
              // Show toast notification
              showToast(
                `ðŸ’° New Sale: â‚¹${amount.toFixed(2)} (${itemCount} items)`,
                'success'
              );
              
              // Call user callback if provided
              onNewSale?.(message.data);
              break;
            }
            
            case 'NEW_ORDER': {
              const orderId = message.data.order_id as string;
              const tableNumber = message.data.table as string;
              
              playDingSound();
              
              showToast(
                `ðŸ½ï¸ New Order #${orderId} for Table ${tableNumber}`,
                'info'
              );
              
              onNewOrder?.(message.data);
              break;
            }
            
            case 'TABLE_READY': {
              const tableNumber = message.data.table as string;
              
              playDingSound();
              
              showToast(
                `âœ… Table ${tableNumber} is ready!`,
                'info'
              );
              
              onTableReady?.(message.data);
              break;
            }
            
            case 'SYSTEM_EVENT': {
              showToast(
                message.data.message as string,
                'info'
              );
              break;
            }
            
            default:
              console.debug(`Unhandled event type: ${message.event}`);
          }
        } catch (error) {
          console.error('Failed to parse WebSocket message:', error);
        }
      };
      
      ws.onerror = (error) => {
        console.error('WebSocket error:', error);
        const errorMsg = 'WebSocket connection error';
        showToast(errorMsg, 'error');
        onError?.(errorMsg);
      };
      
      ws.onclose = () => {
        console.log('WebSocket disconnected');
        isConnectingRef.current = false;
        
        // Attempt to reconnect if enabled
        if (autoReconnect) {
          console.log(`Attempting reconnection in ${reconnectDelay}ms...`);
          reconnectTimeoutRef.current = setTimeout(() => {
            connect();
          }, reconnectDelay);
        }
      };
    } catch (error) {
      console.error('WebSocket connection failed:', error);
      isConnectingRef.current = false;
      
      if (autoReconnect) {
        reconnectTimeoutRef.current = setTimeout(() => {
          connect();
        }, reconnectDelay);
      }
    }
  }, [getToken, autoReconnect, reconnectDelay, onNewSale, onNewOrder, onTableReady, onError]);
  
  /**
   * Disconnect from WebSocket
   */
  const disconnect = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }
    
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }
  }, []);
  
  // Connect on mount, cleanup on unmount
  useEffect(() => {
    connect();
    
    return () => {
      disconnect();
    };
  }, [connect, disconnect]);
  
  return {
    isConnected: wsRef.current?.readyState === WebSocket.OPEN,
    connect,
    disconnect,
  };
}

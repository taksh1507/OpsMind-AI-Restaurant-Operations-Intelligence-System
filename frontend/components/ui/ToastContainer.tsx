'use client';

/**
 * ToastContainer Component
 * 
 * Displays real-time notifications from WebSocket events.
 * Should be placed in root layout for global visibility.
 * 
 * Usage:
 * - Add <ToastContainer /> to your root layout
 * - Use showToast() function from useWebSocket hook to trigger notifications
 */

import React, { useEffect, useState } from 'react';
import { getActiveToasts, onToastChange, dismissToast } from '@/hooks/useWebSocket';
import { X } from 'lucide-react';

interface Toast {
  id: string;
  message: string;
  type: 'success' | 'info' | 'error';
}

export function ToastContainer() {
  const [toasts, setToasts] = useState<Toast[]>([]);
  
  useEffect(() => {
    // Subscribe to toast changes
    const unsubscribe = onToastChange(() => {
      setToasts(getActiveToasts());
    });
    
    return unsubscribe;
  }, []);
  
  if (toasts.length === 0) return null;
  
  return (
    <div className="fixed bottom-4 right-4 z-50 space-y-2 pointer-events-none">
      {toasts.map((toast) => (
        <div
          key={toast.id}
          className={`
            pointer-events-auto
            px-4 py-3 rounded-[3px] shadow-lg border
            flex items-center gap-3
            animate-in slide-in-from-right-4 fade-in duration-300
            ${
              toast.type === 'success'
                ? 'bg-success text-white border-success'
                : toast.type === 'error'
                  ? 'bg-alert text-white border-alert'
                  : 'bg-surface-2 text-foreground border-accent/40'
            }
          `}
        >
          <span className="flex-1">{toast.message}</span>
          <button
            onClick={() => dismissToast(toast.id)}
            className="hover:opacity-80 transition-opacity"
            aria-label="Dismiss notification"
          >
            <X size={16} />
          </button>
        </div>
      ))}
    </div>
  );
}

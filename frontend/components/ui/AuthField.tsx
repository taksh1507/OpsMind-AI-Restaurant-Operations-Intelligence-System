'use client'

import { useId, useState } from 'react'
import { Eye, EyeOff } from 'lucide-react'

interface AuthFieldProps
  extends Omit<React.InputHTMLAttributes<HTMLInputElement>, 'id'> {
  label: string
  icon?: React.ReactNode
  hint?: string
}

/**
 * Labeled input used across the auth pages. Renders an optional leading icon,
 * a consistent focus ring, and — for password fields — a show/hide toggle.
 * All standard input props (value, onChange, autoComplete, required, …) are
 * forwarded so the pages keep full control of their form state.
 */
export function AuthField({
  label,
  icon,
  hint,
  type = 'text',
  className = '',
  ...props
}: AuthFieldProps) {
  const id = useId()
  const [show, setShow] = useState(false)
  const isPassword = type === 'password'
  const inputType = isPassword ? (show ? 'text' : 'password') : type

  return (
    <div className="space-y-1.5">
      <label
        htmlFor={id}
        className="block font-display text-xs font-semibold uppercase tracking-[0.08em] text-cream-dim"
      >
        {label}
      </label>
      <div className="relative">
        {icon && (
          <span className="pointer-events-none absolute inset-y-0 left-0 flex items-center pl-3 text-cream-dim/70">
            {icon}
          </span>
        )}
        <input
          id={id}
          type={inputType}
          className={`w-full rounded-[3px] border border-line bg-surface-2/60 py-2.5 text-foreground placeholder-cream-dim/40 transition-colors focus:border-accent/60 focus:outline-none focus:ring-2 focus:ring-accent/20 disabled:cursor-not-allowed disabled:opacity-50 ${icon ? 'pl-10' : 'pl-3.5'} ${isPassword ? 'pr-11' : 'pr-3.5'} ${className}`}
          {...props}
        />
        {isPassword && (
          <button
            type="button"
            onClick={() => setShow((s) => !s)}
            className="absolute inset-y-0 right-0 flex items-center pr-3 text-cream-dim/70 transition-colors hover:text-accent"
            aria-label={show ? 'Hide password' : 'Show password'}
            tabIndex={-1}
          >
            {show ? <EyeOff size={18} /> : <Eye size={18} />}
          </button>
        )}
      </div>
      {hint && <p className="text-xs text-cream-dim/70">{hint}</p>}
    </div>
  )
}

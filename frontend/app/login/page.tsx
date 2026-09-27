'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { LogIn, AlertCircle, Loader, Mail, Lock } from 'lucide-react'
import apiClient from '@/lib/api-client'
import { AuthShell } from '@/components/ui/AuthShell'
import { AuthField } from '@/components/ui/AuthField'

export default function LoginPage() {
  const router = useRouter()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [isSuccess, setIsSuccess] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)

    // Client-side validation (native validation is disabled via noValidate).
    if (!email.trim()) return setError('Email is required')
    if (!email.includes('@')) return setError('Please enter a valid email address')
    if (!password) return setError('Password is required')

    setIsLoading(true)
    try {
      const response = await apiClient.post('/auth/login', {
        email: email.trim(),
        password,
      })

      const { access_token, token_type, must_change_password } = response.data

      // Store the access token; the refresh token is set by the server as an
      // httpOnly cookie and is intentionally not accessible to JavaScript.
      localStorage.setItem('access_token', access_token)
      localStorage.setItem('token_type', token_type || 'bearer')

      setIsSuccess(true)
      // Teammates on a temporary password must set a real one before entering.
      const next = must_change_password ? '/change-password' : '/'
      setTimeout(() => router.push(next), 500)
    } catch (err: any) {
      const errorMessage = err.response
        ? err.response.data?.detail || 'Login failed. Please check your credentials.'
        : 'Cannot reach the server. Make sure the backend API is running, then try again.'
      setError(errorMessage)
      setIsLoading(false)
    }
  }

  return (
    <AuthShell>
      <div className="rounded-[4px] border border-line bg-surface p-6 shadow-2xl sm:p-8">
        <div className="mb-6">
          <div className="mb-4 inline-flex rounded-[3px] border border-accent/25 bg-accent/10 p-2.5 text-accent">
            <LogIn size={22} />
          </div>
          <h1 className="font-display text-3xl font-bold tracking-wide text-foreground">
            Welcome back
          </h1>
          <p className="mt-1 text-sm text-cream-dim">Sign in to your OpsMind workspace.</p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4" noValidate>
          <AuthField
            label="Email address"
            type="email"
            autoComplete="email"
            placeholder="you@restaurant.com"
            icon={<Mail size={18} />}
            value={email}
            onChange={(e) => {
              setEmail(e.target.value)
              setError(null)
            }}
            disabled={isLoading || isSuccess}
            required
          />
          <AuthField
            label="Password"
            type="password"
            autoComplete="current-password"
            placeholder="Enter your password"
            icon={<Lock size={18} />}
            value={password}
            onChange={(e) => {
              setPassword(e.target.value)
              setError(null)
            }}
            disabled={isLoading || isSuccess}
            required
          />

          {error && (
            <div
              role="alert"
              className="flex items-start gap-2 rounded-[3px] border border-alert/40 bg-alert/10 p-3"
            >
              <AlertCircle className="mt-0.5 flex-shrink-0 text-alert" size={18} />
              <p className="text-sm text-alert">{error}</p>
            </div>
          )}
          {isSuccess && (
            <div className="rounded-[3px] border border-success/40 bg-success/10 p-3">
              <p className="text-sm font-medium text-success">Signed in — redirecting…</p>
            </div>
          )}

          <button
            type="submit"
            disabled={isLoading || isSuccess}
            className="flex w-full items-center justify-center gap-2 rounded-[3px] bg-accent py-3 font-display text-sm font-semibold uppercase tracking-wide text-background shadow-lg transition-colors hover:bg-accent-dim disabled:cursor-not-allowed disabled:opacity-60"
          >
            {isLoading ? (
              <>
                <Loader className="animate-spin" size={18} /> Signing in…
              </>
            ) : isSuccess ? (
              'Authenticated'
            ) : (
              <>
                <LogIn size={18} /> Sign in
              </>
            )}
          </button>
        </form>

        <p className="mt-6 text-center text-sm text-cream-dim">
          Don’t have an account?{' '}
          <Link
            href="/register"
            className="font-semibold text-accent transition-colors hover:text-accent-dim"
          >
            Create one
          </Link>
        </p>
      </div>
    </AuthShell>
  )
}

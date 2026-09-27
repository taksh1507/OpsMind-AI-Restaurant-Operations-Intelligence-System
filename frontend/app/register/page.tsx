'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import {
  UserPlus,
  AlertCircle,
  Loader,
  Mail,
  Lock,
  User,
  UtensilsCrossed,
} from 'lucide-react'
import apiClient from '@/lib/api-client'
import { AuthShell } from '@/components/ui/AuthShell'
import { AuthField } from '@/components/ui/AuthField'

export default function RegisterPage() {
  const router = useRouter()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [fullName, setFullName] = useState('')
  const [restaurantName, setRestaurantName] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [isSuccess, setIsSuccess] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)

    // Client-side validation (native validation is disabled via noValidate).
    if (!email.trim()) return setError('Email is required')
    if (!email.includes('@')) return setError('Please enter a valid email address')
    if (!password) return setError('Password is required (min 8 characters)')
    if (password.length < 8) return setError('Password must be at least 8 characters')

    setIsLoading(true)
    try {
      const response = await apiClient.post('/auth/register', {
        email: email.trim(),
        password,
        full_name: fullName || 'User',
        restaurant_name: restaurantName || 'My Restaurant',
      })

      const { access_token, token_type } = response.data

      // Store the access token; the refresh token is set by the server as an
      // httpOnly cookie and is intentionally not accessible to JavaScript.
      localStorage.setItem('access_token', access_token)
      localStorage.setItem('token_type', token_type || 'bearer')

      setIsSuccess(true)
      setTimeout(() => router.push('/'), 500)
    } catch (err: any) {
      const errorMessage = err.response
        ? err.response.data?.detail || 'Registration failed. Please try again.'
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
            <UserPlus size={22} />
          </div>
          <h1 className="font-display text-3xl font-bold tracking-wide text-foreground">
            Create your account
          </h1>
          <p className="mt-1 text-sm text-cream-dim">Set up your OpsMind workspace.</p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4" noValidate>
          <AuthField
            label="Full name (optional)"
            type="text"
            autoComplete="name"
            placeholder="John Doe"
            icon={<User size={18} />}
            value={fullName}
            onChange={(e) => {
              setFullName(e.target.value)
              setError(null)
            }}
            disabled={isLoading || isSuccess}
          />
          <AuthField
            label="Restaurant name (optional)"
            type="text"
            autoComplete="organization"
            placeholder="Aurora's Kitchen"
            icon={<UtensilsCrossed size={18} />}
            value={restaurantName}
            onChange={(e) => {
              setRestaurantName(e.target.value)
              setError(null)
            }}
            disabled={isLoading || isSuccess}
          />
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
            autoComplete="new-password"
            placeholder="Create a strong password"
            hint="At least 8 characters."
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
              <p className="text-sm font-medium text-success">Account created — redirecting…</p>
            </div>
          )}

          <button
            type="submit"
            disabled={isLoading || isSuccess}
            className="flex w-full items-center justify-center gap-2 rounded-[3px] bg-accent py-3 font-display text-sm font-semibold uppercase tracking-wide text-background shadow-lg transition-colors hover:bg-accent-dim disabled:cursor-not-allowed disabled:opacity-60"
          >
            {isLoading ? (
              <>
                <Loader className="animate-spin" size={18} /> Creating account…
              </>
            ) : isSuccess ? (
              'Account created'
            ) : (
              <>
                <UserPlus size={18} /> Create account
              </>
            )}
          </button>
        </form>

        <p className="mt-6 text-center text-sm text-cream-dim">
          Already have an account?{' '}
          <Link
            href="/login"
            className="font-semibold text-accent transition-colors hover:text-accent-dim"
          >
            Sign in
          </Link>
        </p>
      </div>
    </AuthShell>
  )
}

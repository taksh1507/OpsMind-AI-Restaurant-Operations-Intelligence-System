'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { LogIn, AlertCircle, Loader } from 'lucide-react'
import apiClient from '@/lib/api-client'

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
    setIsLoading(true)

    // Validation
    if (!email.trim()) {
      setError('Email is required')
      setIsLoading(false)
      return
    }

    if (!password) {
      setError('Password is required')
      setIsLoading(false)
      return
    }

    if (!email.includes('@')) {
      setError('Please enter a valid email address')
      setIsLoading(false)
      return
    }

    try {
      // Call login endpoint
      const response = await apiClient.post('/auth/login', {
        email: email.trim(),
        password,
      })

      const { access_token, token_type } = response.data

      // Store token
      localStorage.setItem('access_token', access_token)
      localStorage.setItem('token_type', token_type || 'bearer')

      // Show success
      setIsSuccess(true)

      // Redirect to dashboard
      setTimeout(() => {
        router.push('/')
      }, 500)
    } catch (err: any) {
      const errorMessage = err.response?.data?.detail || 'Login failed. Please check your credentials.'
      setError(errorMessage)
      setIsLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-background flex items-center justify-center p-4">
      {/* Animated background gradient */}
      <div className="absolute inset-0 overflow-hidden">
        <div className="absolute top-0 left-1/4 w-96 h-96 bg-accent/10 rounded-full blur-3xl animate-pulse" />
        <div className="absolute bottom-0 right-1/4 w-96 h-96 bg-accent/5 rounded-full blur-3xl animate-pulse delay-1000" />
      </div>

      {/* Login Card */}
      <div className="relative w-full max-w-md">
        <div className="relative">
          {/* Glowing border effect */}
          <div className="absolute -inset-[2px] bg-accent/10 rounded-[3px] blur-lg opacity-0 transition-opacity duration-500" />

          {/* Main card */}
          <div className="relative bg-surface  border border-accent/20 rounded-[3px] p-8 shadow-2xl">
            {/* Header */}
            <div className="text-center mb-8">
              <div className="flex justify-center mb-4">
                <div className="p-3 bg-accent/10 rounded-[3px] border border-accent/20">
                  <LogIn className="text-accent" size={32} />
                </div>
              </div>
              <h1 className="text-3xl font-bold text-foreground mb-2">Welcome Back</h1>
              <p className="text-cream-dim">Sign in to OpsMind AI</p>
            </div>

            {/* Form */}
            <form onSubmit={handleSubmit} className="space-y-4 mb-6">
              {/* Email Input */}
              <div>
                <label htmlFor="email" className="block text-sm font-display font-semibold tracking-wide text-cream-dim mb-2">
                  Email Address
                </label>
                <input
                  id="email"
                  type="email"
                  value={email}
                  onChange={(e) => {
                    setEmail(e.target.value)
                    setError(null)
                  }}
                  placeholder="demo@aurora-kitchen.com"
                  disabled={isLoading}
                  className="w-full px-4 py-3 bg-surface-2/50 border border-line/50 rounded-[3px] text-foreground placeholder-cream-dim/50 focus:outline-none focus:border-accent/50 focus:ring-2 focus:ring-accent/20 transition-all disabled:opacity-50 disabled:cursor-not-allowed"
                />
              </div>

              {/* Password Input */}
              <div>
                <label htmlFor="password" className="block text-sm font-display font-semibold tracking-wide text-cream-dim mb-2">
                  Password
                </label>
                <input
                  id="password"
                  type="password"
                  value={password}
                  onChange={(e) => {
                    setPassword(e.target.value)
                    setError(null)
                  }}
                  placeholder="Enter your password"
                  disabled={isLoading}
                  className="w-full px-4 py-3 bg-surface-2/50 border border-line/50 rounded-[3px] text-foreground placeholder-cream-dim/50 focus:outline-none focus:border-accent/50 focus:ring-2 focus:ring-accent/20 transition-all disabled:opacity-50 disabled:cursor-not-allowed"
                />
              </div>

              {/* Error Message */}
              {error && (
                <div className="p-3 rounded-[3px] border border-red-500/30 bg-red-900/10 flex items-start gap-2">
                  <AlertCircle className="text-red-400 flex-shrink-0 mt-0.5" size={18} />
                  <p className="text-red-300 text-sm">{error}</p>
                </div>
              )}

              {/* Success Message */}
              {isSuccess && (
                <div className="p-3 rounded-[3px] border border-green-500/30 bg-green-900/10">
                  <p className="text-green-300 text-sm font-display font-semibold tracking-wide">✅ Login successful! Redirecting...</p>
                </div>
              )}

              {/* Login Button */}
              <button
                type="submit"
                disabled={isLoading || isSuccess}
                className="w-full py-3 px-4 bg-accent hover:bg-accent-dim text-background font-semibold rounded-[3px] transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2 shadow-lg hover:shadow-accent/25"
              >
                {isLoading ? (
                  <>
                    <Loader className="animate-spin" size={20} />
                    Signing in...
                  </>
                ) : isSuccess ? (
                  <>
                    ✅ Authenticated
                  </>
                ) : (
                  <>
                    <LogIn size={20} />
                    Sign In
                  </>
                )}
              </button>
            </form>

            {/* Demo Credentials */}
            <div className="p-4 rounded-[3px] bg-accent/5 border border-accent/20">
              <p className="text-cream-dim text-sm mb-2 font-medium">Demo Credentials:</p>
              <div className="space-y-1 text-cream-dim text-sm font-mono">
                <p>📧 demo@aurora-kitchen.com</p>
                <p>🔑 demo123</p>
              </div>
            </div>

            {/* Footer */}
            <div className="mt-6 text-center text-cream-dim text-sm">
              <p>
                {`Don't have an account? `}
                <Link
                  href="/register"
                  className="text-accent hover:text-accent-dim transition-colors font-semibold"
                >
                  Sign up
                </Link>
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Bottom branding */}
      <div className="absolute bottom-8 left-0 right-0 text-center">
        <p className="text-cream-dim text-xs">OpsMind AI © 2026 • Restaurant Operations Intelligence</p>
      </div>
    </div>
  )
}

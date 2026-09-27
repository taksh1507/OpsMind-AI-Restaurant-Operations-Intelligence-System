'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { KeyRound, AlertCircle, Loader, Lock } from 'lucide-react'
import { AuthShell } from '@/components/ui/AuthShell'
import { AuthField } from '@/components/ui/AuthField'
import { changePassword, extractApiError } from '@/lib/team-api'

export default function ChangePasswordPage() {
  const router = useRouter()
  const [currentPassword, setCurrentPassword] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [isSuccess, setIsSuccess] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)
    if (!currentPassword) return setError('Enter your current password')
    if (newPassword.length < 8) return setError('New password must be at least 8 characters')
    if (newPassword !== confirmPassword) return setError('New passwords do not match')
    if (newPassword === currentPassword)
      return setError('New password must be different from the current one')

    setIsLoading(true)
    try {
      const { access_token, token_type } = await changePassword({
        current_password: currentPassword,
        new_password: newPassword,
      })
      // Store the fresh token (old sessions were just revoked server-side).
      localStorage.setItem('access_token', access_token)
      localStorage.setItem('token_type', token_type || 'bearer')
      setIsSuccess(true)
      setTimeout(() => router.push('/'), 600)
    } catch (err) {
      setError(extractApiError(err) || 'Could not change your password. Please try again.')
      setIsLoading(false)
    }
  }

  return (
    <AuthShell>
      <div className="rounded-[4px] border border-line bg-surface p-6 shadow-2xl sm:p-8">
        <div className="mb-6">
          <div className="mb-4 inline-flex rounded-[3px] border border-accent/25 bg-accent/10 p-2.5 text-accent">
            <KeyRound size={22} />
          </div>
          <h1 className="font-display text-3xl font-bold tracking-wide text-foreground">
            Set your password
          </h1>
          <p className="mt-1 text-sm text-cream-dim">
            You&apos;re signed in with a temporary password. Choose a new one to continue.
          </p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4" noValidate>
          <AuthField
            label="Current (temporary) password"
            type="password"
            autoComplete="current-password"
            placeholder="The password you were given"
            icon={<Lock size={18} />}
            value={currentPassword}
            onChange={(e) => {
              setCurrentPassword(e.target.value)
              setError(null)
            }}
            disabled={isLoading || isSuccess}
            required
          />
          <AuthField
            label="New password"
            type="password"
            autoComplete="new-password"
            placeholder="At least 8 characters"
            icon={<Lock size={18} />}
            value={newPassword}
            onChange={(e) => {
              setNewPassword(e.target.value)
              setError(null)
            }}
            disabled={isLoading || isSuccess}
            required
          />
          <AuthField
            label="Confirm new password"
            type="password"
            autoComplete="new-password"
            placeholder="Re-enter your new password"
            icon={<Lock size={18} />}
            value={confirmPassword}
            onChange={(e) => {
              setConfirmPassword(e.target.value)
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
              <p className="text-sm font-medium text-success">Password updated — redirecting…</p>
            </div>
          )}

          <button
            type="submit"
            disabled={isLoading || isSuccess}
            className="flex w-full items-center justify-center gap-2 rounded-[3px] bg-accent py-3 font-display text-sm font-semibold uppercase tracking-wide text-background shadow-lg transition-colors hover:bg-accent-dim disabled:cursor-not-allowed disabled:opacity-60"
          >
            {isLoading ? (
              <>
                <Loader className="animate-spin" size={18} /> Saving…
              </>
            ) : (
              <>
                <KeyRound size={18} /> Update password
              </>
            )}
          </button>
        </form>
      </div>
    </AuthShell>
  )
}

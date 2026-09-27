'use client'

import { useEffect, useState } from 'react'
import { Copy, Check, KeyRound } from 'lucide-react'
import { Modal } from '@/components/ui'
import { createTeamMember, extractApiError } from '@/lib/team-api'
import type { AssignableRole, CreateTeamMemberResult } from '@/types/team'

const inputClass =
  'w-full px-4 py-2 rounded-[3px] bg-background border border-line text-foreground focus:border-accent focus:outline-none transition-colors'
const labelClass =
  'block text-sm font-display font-semibold tracking-wide text-cream-dim mb-2'

interface Props {
  open: boolean
  onClose: () => void
  onCreated: () => void
}

export function TeamMemberFormModal({ open, onClose, onCreated }: Props) {
  const [email, setEmail] = useState('')
  const [role, setRole] = useState<AssignableRole>('staff')
  const [autoGenerate, setAutoGenerate] = useState(true)
  const [tempPassword, setTempPassword] = useState('')
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [created, setCreated] = useState<CreateTeamMemberResult | null>(null)
  const [copied, setCopied] = useState(false)

  useEffect(() => {
    if (open) {
      setEmail('')
      setRole('staff')
      setAutoGenerate(true)
      setTempPassword('')
      setError(null)
      setCreated(null)
      setCopied(false)
    }
  }, [open])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!email.trim() || !email.includes('@')) {
      setError('A valid email is required')
      return
    }
    if (!autoGenerate && tempPassword.trim().length < 8) {
      setError('Temporary password must be at least 8 characters')
      return
    }
    setSaving(true)
    setError(null)
    try {
      const result = await createTeamMember({
        email: email.trim(),
        role,
        temp_password: autoGenerate ? null : tempPassword.trim(),
      })
      setCreated(result)
      onCreated()
    } catch (err) {
      setError(extractApiError(err) || 'Failed to create teammate')
    } finally {
      setSaving(false)
    }
  }

  const copyPassword = async () => {
    if (!created) return
    try {
      await navigator.clipboard.writeText(created.temp_password)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    } catch {
      /* clipboard blocked — owner can still read/select the value manually */
    }
  }

  return (
    <Modal
      open={open}
      title={created ? 'Teammate created' : 'Add teammate'}
      onClose={onClose}
    >
      {created ? (
        <div className="space-y-4">
          <p className="text-sm text-foreground">
            <span className="font-semibold">{created.member.email}</span> can now
            sign in as <span className="capitalize">{created.member.role}</span>.
            Share this one-time password — it won&apos;t be shown again, and they
            must change it on first login.
          </p>
          <div>
            <label className={labelClass}>Temporary password</label>
            <div className="flex items-center gap-2">
              <code className="flex-1 select-all rounded-[3px] border border-line bg-background px-3 py-2 font-mono text-accent">
                {created.temp_password}
              </code>
              <button
                type="button"
                onClick={copyPassword}
                className="flex items-center gap-1.5 px-3 py-2 rounded-[3px] border border-line text-cream-dim hover:text-foreground hover:bg-surface-2 transition-colors"
              >
                {copied ? <Check size={16} className="text-success" /> : <Copy size={16} />}
                {copied ? 'Copied' : 'Copy'}
              </button>
            </div>
          </div>
          <div className="flex justify-end pt-2">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 rounded-[3px] bg-accent text-white font-medium hover:opacity-90 transition-opacity"
            >
              Done
            </button>
          </div>
        </div>
      ) : (
        <form onSubmit={handleSubmit} className="space-y-4">
          {error && (
            <p className="text-sm text-alert bg-alert/10 border border-alert/30 rounded-[3px] px-3 py-2">
              {error}
            </p>
          )}
          <div>
            <label className={labelClass}>Email</label>
            <input
              className={inputClass}
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="teammate@restaurant.com"
              autoFocus
            />
          </div>
          <div>
            <label className={labelClass}>Role</label>
            <select
              className={inputClass}
              value={role}
              onChange={(e) => setRole(e.target.value as AssignableRole)}
            >
              <option value="staff">Staff — view the menu only</option>
              <option value="manager">Manager — sales, insights & menu editing</option>
            </select>
          </div>
          <label className="flex items-center gap-2 text-sm text-foreground">
            <input
              type="checkbox"
              checked={autoGenerate}
              onChange={(e) => setAutoGenerate(e.target.checked)}
              className="accent-accent"
            />
            Generate a temporary password for me
          </label>
          {!autoGenerate && (
            <div>
              <label className={labelClass}>Temporary password</label>
              <input
                className={inputClass}
                type="text"
                value={tempPassword}
                onChange={(e) => setTempPassword(e.target.value)}
                placeholder="At least 8 characters"
              />
            </div>
          )}
          <div className="flex justify-end gap-3 pt-2">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 rounded-[3px] border border-line text-cream-dim hover:text-foreground hover:bg-surface-2 transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={saving}
              className="flex items-center gap-2 px-4 py-2 rounded-[3px] bg-accent text-white font-medium hover:opacity-90 transition-opacity disabled:opacity-50"
            >
              <KeyRound size={16} /> {saving ? 'Creating…' : 'Create teammate'}
            </button>
          </div>
        </form>
      )}
    </Modal>
  )
}

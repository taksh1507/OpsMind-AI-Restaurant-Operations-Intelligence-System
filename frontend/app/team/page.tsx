'use client'

import { useState } from 'react'
import useSWR from 'swr'
import { Users, UserPlus, Trash2, ShieldCheck, ShieldOff, Lock, KeyRound } from 'lucide-react'
import { StatCard } from '@/components/ui'
import { TeamMemberFormModal } from '@/components/team/TeamMemberFormModal'
import { useUserRole } from '@/hooks/useUserRole'
import { showToast } from '@/hooks/useWebSocket'
import {
  fetchTeam,
  updateTeamMember,
  deleteTeamMember,
  extractApiError,
} from '@/lib/team-api'
import type { TeamMember, AssignableRole } from '@/types/team'

export default function TeamPage() {
  const { isOwner, userId, loading: roleLoading } = useUserRole()
  const { data, error, isLoading, mutate } = useSWR('team:all', fetchTeam, {
    revalidateOnFocus: false,
  })
  const [modalOpen, setModalOpen] = useState(false)

  const members = data ?? []
  const activeCount = members.filter((m) => m.is_active).length
  const pendingCount = members.filter((m) => m.must_change_password).length

  const changeRole = async (m: TeamMember, role: AssignableRole) => {
    try {
      await updateTeamMember(m.id, { role })
      showToast('Role updated', 'success')
      await mutate()
    } catch (e) {
      showToast(extractApiError(e) || 'Update failed', 'error')
    }
  }

  const toggleActive = async (m: TeamMember) => {
    try {
      await updateTeamMember(m.id, { is_active: !m.is_active })
      showToast(m.is_active ? 'Access revoked' : 'Access restored', 'success')
      await mutate()
    } catch (e) {
      showToast(extractApiError(e) || 'Update failed', 'error')
    }
  }

  const remove = async (m: TeamMember) => {
    if (!window.confirm(`Remove ${m.email}? They will lose access immediately.`)) return
    try {
      await deleteTeamMember(m.id)
      showToast('Teammate removed', 'success')
      await mutate()
    } catch (e) {
      showToast(extractApiError(e) || 'Delete failed', 'error')
    }
  }

  return (
    <div className="space-y-8">
      <div className="border-b border-accent/20 pb-6 flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="font-display text-4xl font-bold text-foreground mb-1 flex items-center gap-3">
            <Users size={32} className="text-accent" />
            Team &amp; Access
          </h1>
          <p className="text-cream-dim">
            {isOwner
              ? 'Create staff and manager logins and control what they can access'
              : 'Your restaurant’s team'}
          </p>
        </div>
        {isOwner && (
          <button
            onClick={() => setModalOpen(true)}
            className="flex items-center gap-2 px-4 py-2 rounded-[3px] bg-accent text-white font-medium hover:opacity-90 transition-opacity"
          >
            <UserPlus size={18} /> Add teammate
          </button>
        )}
      </div>

      {!isOwner && !roleLoading && (
        <div className="flex items-center gap-2 text-sm text-cream-dim bg-surface-2 border border-line rounded-[3px] px-4 py-2">
          <Lock size={14} className="text-accent" />
          Only the owner can add teammates or change access.
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <StatCard title="Team Members" value={`${members.length}`} icon={<Users size={24} />} />
        <StatCard title="Active" value={`${activeCount}`} icon={<ShieldCheck size={24} />} />
        <StatCard
          title="Pending Setup"
          value={`${pendingCount}`}
          description="Still on a temporary password"
          icon={<KeyRound size={24} />}
        />
      </div>

      {isLoading && <p className="text-cream-dim">Loading team…</p>}
      {error && (
        <p className="text-alert bg-alert/10 border border-alert/30 rounded-[3px] px-4 py-3">
          {extractApiError(error) || 'Failed to load the team. Please refresh to retry.'}
        </p>
      )}

      {!isLoading && !error && (
        <div className="ticket-perf rounded-[3px] border border-line bg-surface overflow-hidden">
          {members.length === 0 ? (
            <p className="px-6 py-8 text-sm text-cream-dim text-center">
              No teammates yet.
            </p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-line text-cream-dim">
                    <th className="text-left py-3 px-6">Member</th>
                    <th className="text-left py-3 px-4">Role</th>
                    <th className="text-center py-3 px-4">Status</th>
                    {isOwner && <th className="text-right py-3 px-6">Actions</th>}
                  </tr>
                </thead>
                <tbody>
                  {members.map((m) => {
                    const isSelf = m.id === userId
                    const isOwnerRow = m.role === 'owner'
                    const canAct = isOwner && !isSelf && !isOwnerRow
                    return (
                      <tr
                        key={m.id}
                        className="border-b border-line/50 hover:bg-surface-2/40 transition-colors"
                      >
                        <td className="py-3 px-6">
                          <div className="text-foreground font-medium">
                            {m.email}
                            {isSelf && <span className="ml-2 text-xs text-cream-dim">(you)</span>}
                          </div>
                          {m.must_change_password && (
                            <div className="text-xs text-accent flex items-center gap-1 mt-0.5">
                              <KeyRound size={12} /> Temporary password — must reset on login
                            </div>
                          )}
                        </td>
                        <td className="py-3 px-4">
                          {canAct ? (
                            <select
                              value={m.role}
                              onChange={(e) => changeRole(m, e.target.value as AssignableRole)}
                              className="px-2 py-1 rounded-[3px] bg-background border border-line text-foreground focus:border-accent focus:outline-none"
                            >
                              <option value="staff">Staff</option>
                              <option value="manager">Manager</option>
                            </select>
                          ) : (
                            <span className="capitalize text-cream-dim">{m.role}</span>
                          )}
                        </td>
                        <td className="py-3 px-4 text-center">
                          {m.is_active ? (
                            <span className="text-xs text-success">Active</span>
                          ) : (
                            <span className="text-xs text-cream-dim">Disabled</span>
                          )}
                        </td>
                        {isOwner && (
                          <td className="py-3 px-6">
                            <div className="flex items-center justify-end gap-2">
                              {canAct ? (
                                <>
                                  <button
                                    type="button"
                                    title={m.is_active ? 'Revoke access' : 'Restore access'}
                                    aria-label={m.is_active ? 'Revoke access' : 'Restore access'}
                                    onClick={() => toggleActive(m)}
                                    className="p-1.5 rounded-[3px] border border-line text-cream-dim hover:text-foreground hover:bg-surface-2 transition-colors"
                                  >
                                    {m.is_active ? <ShieldOff size={16} /> : <ShieldCheck size={16} />}
                                  </button>
                                  <button
                                    type="button"
                                    title="Remove"
                                    aria-label="Remove teammate"
                                    onClick={() => remove(m)}
                                    className="p-1.5 rounded-[3px] border border-line text-cream-dim hover:text-alert hover:border-alert/50 transition-colors"
                                  >
                                    <Trash2 size={16} />
                                  </button>
                                </>
                              ) : (
                                <span className="text-xs text-cream-dim">—</span>
                              )}
                            </div>
                          </td>
                        )}
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      <TeamMemberFormModal
        open={modalOpen}
        onClose={() => setModalOpen(false)}
        onCreated={() => mutate()}
      />
    </div>
  )
}

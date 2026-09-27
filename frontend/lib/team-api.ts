// Thin API layer for team management (owner-driven staff/manager accounts) and
// self-service password change. Wraps the tenant-scoped endpoints in
// app/api/users.py and app/api/auth.py. Create/update/delete require OWNER
// server-side; listing allows OWNER or MANAGER.

import apiClient from './api-client'
import type {
  TeamMember,
  CreateTeamMemberInput,
  CreateTeamMemberResult,
  UpdateTeamMemberInput,
  ChangePasswordInput,
} from '@/types/team'

export async function fetchTeam(): Promise<TeamMember[]> {
  const { data } = await apiClient.get<TeamMember[]>('/users')
  return data
}

export async function createTeamMember(
  input: CreateTeamMemberInput,
): Promise<CreateTeamMemberResult> {
  const { data } = await apiClient.post<CreateTeamMemberResult>('/users', input)
  return data
}

export async function updateTeamMember(
  id: number,
  input: UpdateTeamMemberInput,
): Promise<TeamMember> {
  const { data } = await apiClient.put<TeamMember>(`/users/${id}`, input)
  return data
}

export async function deleteTeamMember(id: number): Promise<void> {
  await apiClient.delete(`/users/${id}`)
}

/**
 * Change the current user's own password (also clears the must-change flag).
 * The server revokes old sessions and returns a fresh access token, which the
 * caller should store so the current session keeps working.
 */
export async function changePassword(
  input: ChangePasswordInput,
): Promise<{ access_token: string; token_type: string }> {
  const { data } = await apiClient.post<{
    access_token: string
    token_type: string
  }>('/auth/change-password', input)
  return data
}

// Re-export so callers get one import site for menu-style error extraction.
export { extractApiError } from './menu-api'

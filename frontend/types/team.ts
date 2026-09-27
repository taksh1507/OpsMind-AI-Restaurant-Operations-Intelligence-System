// Team management domain types. Mirrors the backend team schemas in
// app/models/schemas.py (TeamMemberResponse / CreateTeamMember* / etc.).

// Roles an owner can assign to a teammate. OWNER is deliberately not assignable.
export type AssignableRole = 'manager' | 'staff'

export interface TeamMember {
  id: number
  email: string
  role: 'owner' | 'manager' | 'staff'
  is_active: boolean
  must_change_password: boolean
  created_at: string
}

export interface CreateTeamMemberInput {
  email: string
  role: AssignableRole
  // Optional: when omitted the server generates a one-time password and returns it.
  temp_password?: string | null
}

export interface CreateTeamMemberResult {
  member: TeamMember
  // Shown to the owner exactly once so they can hand it to the teammate.
  temp_password: string
}

export interface UpdateTeamMemberInput {
  role?: AssignableRole
  is_active?: boolean
}

export interface ChangePasswordInput {
  current_password: string
  new_password: string
}

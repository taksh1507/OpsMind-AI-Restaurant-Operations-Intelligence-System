# Staff Accounts & Roles

*Phase 2 — shipped.*

## What it does

You create a login for each person on your team and give them a role. The role
decides what they can see and do. New staff get a **one-time temporary
password** and are **forced to set their own password** the first time they log
in — so you never know or store their real password.

## The three roles

| Role | Can do |
|------|--------|
| **Owner** | Everything: menu, staff, settings, billing, all analytics. There is one owner (you). |
| **Manager** | Sales, analytics, AI insights, view the team, edit the menu. Cannot manage staff, settings, or billing. |
| **Staff** | Limited operational views only. |

## How to use it

Open **Team** in the sidebar.

1. **Add team member** — enter their email and pick a role (Manager or Staff).
2. OpsMind creates the account and shows a **temporary password** — **once**.
   Copy it now; it is not shown again.
3. Share that temporary password with the person over a trusted channel (in
   person, or a secure message).
4. On their **first login**, they must set a new password of their own. From
   then on, only they know it.
5. **Change a role or remove someone** any time from the Team page.

> Changing a password (including the forced first-login change) revokes any
> existing sessions, so an old temporary password can't be reused.

## Who can use it

- **Create, change role, or remove** team members — **Owner only**.
- **View the team list** — Owners and Managers.

All of these checks run on the server.

## Security notes

- Passwords are hashed with **Argon2** — plain passwords are never stored.
- The temporary password is shown exactly once and must be changed on first
  login.
- Staff accounts are scoped to your restaurant (`tenant_id`); a staff member can
  never see another restaurant's data.
- Managing staff is Owner-only, enforced server-side.
- See the full model in [Security](../security.md).

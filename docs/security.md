# Security Model

This page describes how OpsMind protects accounts and data. It separates what is
**in place today** from what is **planned**, so there are no surprises.

## Multi-tenant data isolation

- Every restaurant is a separate **tenant**. Menus, sales, staff, reviews, and
  settings all carry a `tenant_id`, and every query is scoped to the logged-in
  user's tenant.
- One restaurant can never read or write another restaurant's data.
- Owner-only actions (staff management, settings) are enforced on the server,
  not just hidden in the UI.

## Authentication

- **Passwords** are hashed with **Argon2** (via passlib; bcrypt kept for
  backward compatibility). Plain passwords are never stored.
- **Login** issues a short-lived **JWT access token**. A **refresh token** is
  delivered only as an **httpOnly cookie** (not readable by JavaScript, which
  limits XSS token theft) and is stored **hashed** on the server.
- **Login rate limiting:** after **5 failed attempts** from an IP, further
  attempts are blocked for a **5-minute** window.
- **Staff onboarding:** the owner sets a **one-time temporary password**; the
  staff member is **forced to change it on first login**. Changing a password
  revokes existing refresh tokens.

## Authorization (roles)

Three preset roles, enforced by server-side dependencies:

| Role | Can do |
|------|--------|
| **Owner** | Everything: menu, staff, settings, billing, all analytics |
| **Manager** | Sales, analytics, AI insights (no staff/settings/billing) |
| **Staff** | Limited operational views only |

## Network & transport

- **CORS** is restricted to a configured allow-list of front-end origins
  (not open to any site).
- Run OpsMind behind HTTPS in production so tokens and cookies are encrypted in
  transit (deployment responsibility).

## Secrets & AI credentials

- API keys and database credentials come from **environment variables** and are
  **never committed** to the repository.
- AI provider credentials (Anthropic Claude) are read from the environment at
  runtime. Secret values are not written to logs.

## AI-specific safety (agentic features)

Per-tenant **AI usage limits (Phase 4, shipped)** are already in place: every AI
call's token use is metered per restaurant and a monthly cap is enforced
**server-side, before the AI call runs**, so cost and abuse are bounded and one
restaurant can never spend another's allowance. See
[AI Usage & Limits](features/ai-usage-metering.md).

As the agentic assistant lands (see [Roadmap](roadmap.md)), these additional
guardrails apply:

- The AI's tools receive the `tenant_id` **from the server**, never from the
  model or the user — so the assistant physically cannot reach another
  restaurant's data.
- Agent tools are **read-only** to start; there is a hard cap on how many tool
  calls a single request may make.

## Planned hardening (not yet shipped)

- **Audit log** of sensitive actions — staff changes, settings changes, logins
  (Phase 8).
- **Encrypted storage** for third-party OAuth tokens (POS integration, Phase 9).
- **Webhook signature verification** and no card-data storage for billing
  (Phase 10).

If you believe you've found a security issue, do not open a public issue —
contact the project maintainer directly.

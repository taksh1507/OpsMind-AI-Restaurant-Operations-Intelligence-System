# Roadmap

How OpsMind is evolving from a demo into a product any restaurant can use.
Status: ✅ shipped · 🔜 next · ⏳ planned · 🔑 needs external account/keys.

## Shipped

- ✅ **Phase 1 — Menu management.** Tenant-scoped menu CRUD with price
  validation and availability filters.
- ✅ **Phase 2 — Staff accounts & permissions.** Owner-created logins,
  one-time temporary passwords, forced password change on first login, and
  Owner/Manager/Staff role presets.
- ✅ **Phase 3 — AI & model preferences.** Per-tenant settings: choose the
  Claude model, toggle AI insights and weather signals, set default city and
  timezone. Analytics and the daily tip honor these preferences.
- ✅ **Phase 4 — AI usage metering + guardrails.** Every AI call's token use is
  metered per restaurant, a monthly cap is enforced (over-cap requests get a
  clear "limit reached" message instead of running), and owners can see
  month-to-date usage broken down by feature.

## Planned

Each phase is built and verified independently, then documented in
[`features/`](features/). Order may change based on priorities.

- 🔜 **Phase 5 — "Ask OpsMind" assistant (agentic AI).** A conversational
  assistant that can pull your own sales, menu, weather, reviews, and forecasts
  to answer open questions ("why did revenue dip last week?"). Built on Claude
  tool-use, tenant-scoped and read-only, streamed live. *(Depends on Phase 4.)*
- ⏳ **Phase 6 — Autonomous nightly ops agent.** Runs on a schedule to spot
  anomalies (revenue dips, margin alerts, bad reviews) and post a morning
  briefing per restaurant. *(Depends on Phase 5.)*
- ⏳ **Phase 7 — Currency & localization.** Per-restaurant currency (today the
  system assumes INR in places) so restaurants anywhere can use it correctly.
- ⏳ **Phase 8 — Staff invite links + audit log.** Single-use invite links so
  staff set their own password (no email server needed), plus an audit trail of
  sensitive actions.
- ⏳ **Phase 9 — Menu import + POS integration.** 🔑 Bulk menu import (CSV) and a
  point-of-sale connector (Square first) so new restaurants get value on day
  one. *POS requires a Square developer account; built behind an interface with
  a test provider until real keys are supplied.*
- ⏳ **Phase 10 — Billing & subscription plans.** 🔑 Subscription tiers that gate
  the Phase 4 usage caps. *Requires a Stripe account and keys; built behind an
  interface with a mock provider until real keys are supplied.*
- ⏳ **Phase 11 — Multi-location + data export.** Multiple locations under one
  restaurant group (for chains), plus CSV/PDF export and scheduled report
  digests.

## External dependencies you'll need to provide

Two phases connect to outside services and can't be fully finished without
accounts/keys. We build them **behind a provider interface with a working
test/mock implementation**, so the code is complete and testable now, and
switching to the real service is just configuration:

| Phase | Needs from you |
|-------|----------------|
| 9 (POS) | A **Square developer app** (client ID/secret) for live POS sync |
| 10 (Billing) | A **Stripe account** (API keys + webhook signing secret) |

## Principles

- **No hallucinated features.** Docs and status reflect code that actually
  ships and passes its smoke test.
- **Security first.** Every phase lists its security measures; see
  [security.md](security.md).
- **Verify before "done."** Each phase is smoke-tested (Docker + API calls)
  before it's marked complete.

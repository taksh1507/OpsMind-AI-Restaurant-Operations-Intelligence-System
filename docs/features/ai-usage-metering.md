# AI Usage & Limits

*Phase 4 — shipped.*

## What it does

OpsMind's smart features (your daily tip, forecasts, margin advice, review
replies) are powered by Claude AI. Every time one of them runs, it uses a small
amount of AI — measured in **tokens** (think of tokens as the "words" the AI
reads and writes). This feature keeps those costs visible and under control:

- **Metering** — each AI feature records how many tokens it used, for *your*
  restaurant only.
- **A monthly limit** — each restaurant has a monthly token allowance. If you
  reach it, AI features pause with a clear message instead of running up an
  open-ended bill. The allowance resets at the start of each month.
- **An owner usage view** — see your month-to-date usage at a glance, including
  which features are using the most.

This is what makes it safe to offer powerful AI to every restaurant: no surprise
spend, and one restaurant can never use up another's allowance.

## Which features count

These AI features record usage:

- Daily tip (weather-aware promotion)
- Strategic briefing
- Margin / pricing analysis
- Review-response drafting
- Labor-efficiency analysis
- Revenue forecast

Things that **don't** cost tokens (and so don't count):

- The **customer persona / VIP briefing**, which is computed locally from your
  own data (no Claude call).
- A **cached** briefing — if the same briefing was generated recently, OpsMind
  reuses it instead of calling the AI again, so it costs nothing.

## How to use it

Open your usage view (Owner only):

```
GET /api/v1/ai-usage
```

You'll get back this month's numbers, for example:

- **tokens_used / tokens_remaining** — how much of your allowance you've used and
  what's left.
- **percent_used** — how close you are to the cap.
- **monthly_token_cap** — your allowance for the month (or `null` if limits are
  turned off for this deployment).
- **by_feature** — a breakdown showing which features used the most tokens.
- **period_label** — the month these numbers cover (e.g. "September 2026").

### What happens when you hit the limit

- AI features return **"Monthly AI usage limit reached"** (HTTP 429) instead of
  running. Nothing is charged for a blocked request — the limit is checked
  *before* any AI call is made.
- Everything non-AI (menu, sales, team, settings) keeps working normally.
- The allowance **resets automatically** at the start of the next month.
- Need more before then? Whoever hosts your OpsMind can raise the limit (see
  below).

## Setting the limit

The monthly cap is a **deployment setting**, chosen by the person hosting
OpsMind (not from inside the app):

- Set `AI_MONTHLY_TOKEN_CAP` in the server environment (see
  [Deployment](../deployment.md) and `.env.example`). The default is
  1,500,000 tokens per restaurant per month.
- Set it to `0` (or a negative number) to **disable** enforcement entirely —
  usage is still metered and visible, just never blocked.

The same cap applies to each restaurant independently.

## Who can use it

- **View usage** — **Owner only.** AI spend is an operational/billing concern,
  so the usage view is restricted to the Owner and enforced server-side.
- **The limit itself** applies to *everyone* in your restaurant who triggers an
  AI feature (Owner and Manager alike) — it protects the whole restaurant's
  allowance, not one person's.

## Security notes

- Every usage record and every limit check carries your `tenant_id`; they only
  ever affect **your** restaurant. One restaurant's usage can't touch another's.
- The cap is enforced **server-side, before** any AI request runs — it can't be
  bypassed from the browser.
- Only the Owner can read the usage view (enforced server-side).
- Metering is **best-effort and non-blocking**: if recording usage ever fails,
  it's logged and ignored so it can never break the AI feature you asked for.
- The limit comes from the **server's environment**, never from the browser, so
  a user can't raise their own cap.
- See the full model in [Security](../security.md).

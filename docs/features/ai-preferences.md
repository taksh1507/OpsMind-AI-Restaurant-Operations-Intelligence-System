# AI & Model Preferences

*Phase 3 — shipped.*

## What it does

Every restaurant controls its own AI behavior from **Settings**. You pick which
Claude model does the analysis, turn AI insights and weather signals on or off,
and set your default city and timezone. Every AI feature — the daily tip,
forecasts, margin analysis — honors these choices immediately.

## The settings

**Restaurant Information**
- **Restaurant name** — shown across reports and daily tips.
- **Timezone** — so "today" and daily reports line up with your local day.
- **Default city** — used for weather-aware recommendations. Leave it blank to
  clear it.

**AI Configuration**
- **AI model** — how powerful vs. fast the AI is:
  - *Opus* — most capable, deepest analysis (default).
  - *Sonnet* — balanced speed and quality.
  - *Haiku* — fastest and most economical.
- **AI Insights** toggle — turns AI-generated tips and narratives on/off.
- **Weather Signals** toggle — factors local weather into daily tips.

Click **Save Changes**. Choices apply right away.

## How the toggles affect features

The daily tip (and other AI features) check your settings first:

- If **AI Insights** is off, AI features report themselves as *disabled* instead
  of running.
- If **Weather Signals** is off, weather is not pulled into tips.
- If a feature needs a city and you haven't set a **default city** (and didn't
  pass one), it asks you to set one rather than guessing.

So if a tip won't show, open Settings and confirm AI Insights and Weather are on
and a default city is set.

## Who can use it

**Owner only.** Settings cover AI spend and operational defaults for the whole
restaurant, so the page and its API are restricted to the Owner and enforced
server-side. Managers and Staff don't see it.

## Security notes

- Settings carry your `tenant_id`; they only ever affect **your** restaurant.
- AI provider credentials come from the server's environment — never from this
  page and never exposed to the browser.
- Only the Owner can read or change these preferences.
- See the full model in [Security](../security.md).

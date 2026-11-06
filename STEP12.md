# Step 12: AI safety and cost controls

Implemented safeguards for AI inputs, outputs, provider calls, and monthly usage.

- Untrusted review, customer, menu, recommendation, and metrics data is escaped, length-capped, and passed in clearly delimited input blocks with instructions to ignore embedded commands.
- Review and customer-persona responses are validated against strict Pydantic schemas before use; cached JSON is validated before being returned.
- Anthropic requests use configured timeouts, retries, and output-token caps. Sampling parameters unsupported by current Claude models are omitted. The selectable model list comes from configuration.
- Client-facing provider and parsing failures use generic messages while details go to server logs.
- Monthly usage is reserved atomically before paid calls, preventing concurrent requests from exceeding the configured token cap. Reservations are finalized against actual usage or released after errors.
- Added Alembic migration `0002_ai_usage_budgets` to preserve existing monthly usage when upgrading.

Verification: `pytest -q` passed (292 passed, 2 skipped); focused AI safety tests passed (6 passed); the budget migration was checked on SQLite, including carry-forward of existing usage; `python -m compileall app` passed. Live Anthropic calls were not run because no API key is configured. PostgreSQL atomic reservation is implemented using its native upsert path; this environment's test suite was run against SQLite.

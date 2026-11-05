# Real-time sale notifications

Connect to `/api/v1/ws` on the API host. The frontend derives this URL from
`NEXT_PUBLIC_API_URL` (which includes `/api/v1`) and converts HTTP(S) to WS(S).
Set this value in `frontend/.env.local` or the frontend build environment;
the backend's root `.env` does not configure the Next.js build. Rebuild the
frontend after changing it.
Allow the frontend's exact origin in `CORS_ORIGINS`; missing or unlisted
origins and URL query credentials are rejected. Use HTTPS/WSS in production.

Within five seconds, send `{"event":"AUTH","token":"<access token>"}` as
the first text frame. Tokens never go in URLs. The server validates the JWT,
tenant ownership, account status, token version and temporary-password flag.
It closes the database session immediately after authentication.

After `CONNECTED`, send the literal text `ping` every 15 seconds. The server
responds with `{"event":"PONG","data":{}}`; idle connections close after
60 seconds. Connections close at access-token expiry (code 4001). The browser
refreshes through the HTTP auth flow before reconnecting. Already-open sockets
retain their authenticated identity until expiry; a later password/role change
does not revoke an existing socket immediately. No client-initiated business
events are accepted.

Sale events use `{"event":"NEW_SALE","data":{"sale_id":1,"amount":10,
"tax_amount":0,"item_count":1,"payment_method":"cash"},"tenant_id":1,
"timestamp":"<UTC ISO timestamp>"}`. `item_count` counts units, not lines.
Notifications are best effort: a Redis outage cannot undo a committed sale.
Refresh sales history to recover events missed while disconnected.

Default limits are 100 connections per tenant, five per user, 4 KiB per incoming
message, five seconds to authenticate and three seconds per send. See the
`WS_*` settings in `.env.example`. Broadcasts send concurrently; timed-out
clients are closed and removed. The frontend validates event payloads, sends
heartbeats and uses exponential backoff with up to six consecutive retries.
Authentication pages do not connect; unmount/logout cancels reconnect timers.

Without `REDIS_URL`, use exactly **one worker**. Multiple workers fail config
validation without Redis. With Redis, every worker subscribes to a shared
channel; atomic Redis leases enforce tenant/user caps across workers and expire
after crashes. A subscriber failure closes its clients and refuses new ones;
restart that worker to restore service. Redis must be private to the app.
`GET /api/v1/ws/stats` requires a manager/owner and exposes only their tenant's
connections on the current worker; it is not a cluster-wide count.

The Docker Gunicorn worker applies transport frame/queue limits. For a direct
CLI launch use `uvicorn app.main:app --no-proxy-headers --ws-max-size 4096
--ws-max-queue 4 --ws-ping-interval 20 --ws-ping-timeout 20`, or run
`python -m app.main`. If changing `WS_MAX_MESSAGE_BYTES`, change the CLI frame
limit too. Do not add proxy-header trust to the ASGI server independently of
the application's trusted-proxy configuration.

Browser check: log in as the same tenant in two tabs. Leave one on the dashboard
and create a sale from the other client. The dashboard should show an INR sale
toast. A different tenant must not receive it. Import UI is at `/import-sales`
(manager/owner only), with a downloadable CSV template and row-level results.

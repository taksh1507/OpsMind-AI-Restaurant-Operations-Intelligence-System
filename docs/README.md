# OpsMind Documentation

OpsMind is an AI-powered operations assistant for restaurants. Each restaurant
gets its own private workspace (a "tenant") where the owner manages their menu,
staff, sales data, and AI preferences — and gets AI-generated insights about
revenue, margins, customer reviews, and staffing.

This folder explains how to set up and use the system. Start with the guide that
matches you:

## For restaurant owners & staff (non-technical)
- **[Getting Started](getting-started.md)** — create your account, add your menu,
  invite staff, and turn on AI insights. No technical knowledge needed. Includes
  a short FAQ at the end.

## For the person running/hosting OpsMind (technical)
- **[Deployment](deployment.md)** — running OpsMind with Docker.
- **[Security Model](security.md)** — how accounts, data, and AI access are
  protected, and what each restaurant's data is isolated from.
- **[Architecture Overview](../ARCHITECTURE.md)** — how the system is built
  (top-level document).

## Roadmap & feature docs
- **[Roadmap](roadmap.md)** — what is built and what is planned next.
- **[features/](features/)** — one page per major feature, added as each ships.

## What "used by all restaurants" means here
OpsMind is multi-tenant: one running server can host many independent
restaurants at once. Every restaurant's menu, sales, staff, and settings are
kept strictly separate (see [Security Model](security.md)). An owner never sees
another restaurant's data.

> Docs are kept accurate to the code that is actually shipped. If something in a
> guide doesn't match what you see in the app, it's a bug in the docs — please
> flag it.

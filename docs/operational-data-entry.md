# Operational data entry

All paths below start with `/api/v1`. Use the access token returned by
`POST /auth/register` or `POST /auth/login` as `Authorization: Bearer <token>`.
The authenticated tenant determines ownership; request bodies cannot set it.

| Resource | Methods | Permissions |
| --- | --- | --- |
| `/customers` | POST, GET list; GET, PUT, DELETE `/{id}` | Owner/manager writes; authenticated tenant users read |
| `/ingredients` | POST, GET list; GET, PUT, DELETE `/{id}` | Owner/manager |
| `/recipes` | POST, GET list; GET, PUT, DELETE `/{id}` | Owner/manager |
| `/staff` | POST, GET list; GET, PUT, DELETE `/{id}` | Owner/manager |
| `/shifts` | POST, GET list; GET, PUT, DELETE `/{id}` | Owner/manager |
| `/waste-logs` | POST, GET list; GET, PUT, DELETE `/{id}` | Owner/manager |
| `/reviews` | POST, GET list | Owner/manager |

Lists accept `limit` (1–200, default 50) and `offset` (nonnegative). Creates
return 201, replacements 200, deletes 204. PUT replaces all editable fields;
send the same full shape as POST. Foreign and nonexistent records or parent IDs
return the same 404. Duplicate customer emails within the tenant return 409.
Emails are normalized to lowercase by the customer API. Extra fields are rejected.
The interactive API schema is available in development.

## Fresh tenant workflow

Create a category and menu item using the existing `/categories` and
`/menu-items` endpoints. Use their returned IDs in subsequent requests. All
prices, unit costs, wages and waste costs below are INR.

```jsonc
// POST /customers
{"name":"Asha","email":"asha@example.com","preferences":{"allergies":["nuts"]}}

// POST /ingredients
{"name":"Rice","unit":"kg","unit_cost":"40.0000"}

// POST /recipes — IDs are examples; use the returned ingredient and menu IDs.
{"menu_item_id":1,"ingredient_id":1,"quantity_used":0.5}

// POST /staff — payroll/roster records, separate from login accounts at /users.
{"name":"Chef","role":"chef","hourly_rate":"120.00"}

// POST /shifts — explicit timezone offsets required, maximum duration 24 hours.
{"staff_id":1,"start_time":"2026-10-23T09:00:00+05:30","end_time":"2026-10-23T17:00:00+05:30"}

// POST /waste-logs — quantity uses the ingredient unit; record the actual loss.
{"ingredient_id":1,"quantity_wasted":0.5,"reason":"Spoiled","cost_lost_inr":"20.00","timestamp":"2026-10-23T12:00:00+05:30"}

// POST /reviews
{"customer_name":"Asha","rating":5,"comment":"Excellent food","source":"internal"}

// POST /sales — links the returned customer; tax_rate is a fraction.
{"customer_id":1,"items":[{"menu_item_id":1,"quantity":2}],"tax_rate":"0.05","payment_method":"upi"}
```

The snippets use JSON-with-comments for explanation; omit the comments in HTTP
bodies. Available waste reasons are `Expired`, `Overcooked` and `Spoiled`.
Sentiment is processed on review creation with the local classifier, falling
back to a local keyword heuristic. Creating reviews never invokes paid AI.
The stored sentiment score ranges from -1 to 1. It is an automated estimate.

Customer visits count completed transactions, including CSV imports. Spending
includes tax, whereas sales analytics revenue excludes tax. Sale creation and
customer increments commit atomically; failed sales do not increment totals.
CSV retries do not double-count an already imported order. Customer totals
cannot be supplied or edited through customer request bodies.
`GET /customers/{id}/briefing` reads actual sale line items and the customer
totals; it no longer needs seeded purchase history.

## Analytics and record retention

Recipes feed `/analytics/margin-report`; staff and shifts feed
`/analytics/staffing-plan?analysis_date=YYYY-MM-DD` (UTC date); reviews feed
`/analytics/reputation`; waste logs feed `/analytics/sustainability`.
Margin costs use current ingredient costs; staffing costs use current hourly
rates. They are estimates rather than immutable historical cost accounting.
AI narratives and forecasts still require their respective credentials or
trained models. API-to-analytics regression tests mock AI calls, while checking
the real database calculations. No live Anthropic verification is claimed.

Sustainability exposes actual waste costs and normalizes `kg` and `g` to kg.
Other units remain included in waste costs and log counts, but are excluded
from weight reductions and CO2 estimates, with an excluded count in the response.
CO2 uses a disclosed illustrative factor of 2.5 kg per kg; it is not measured
emissions. A missing prior weight baseline yields zero reduction.

Deleting a customer unlinks sales and preserves their transaction history.
Delete a staff record's shifts first, or deactivate the staff record instead.
Delete related recipes and waste logs before deleting an ingredient. Changing
an ingredient unit is blocked while related recipes or waste logs exist, to
avoid reinterpreting their recorded quantities. These conflicts return 409.

## Existing customer totals

No new database columns are needed for these endpoints. Existing installations
must already have applied the earlier customer tenant migration. If old sales
were recorded without updating customer counters, back up the database and
pause writes during maintenance, then run once per verified tenant ID:

```powershell
python -m scripts.rebuild_customer_totals --tenant-id 1
```

The command uses `DATABASE_URL` from configuration, locks the selected tenant's
customers and rebuilds counts and tax-inclusive spending from that tenant's
linked sales in one transaction. It is repeatable and does not modify other
tenants. It cannot recover a customer link that was never recorded. It has
been exercised against temporary test databases only; it has not been run
against your application database.

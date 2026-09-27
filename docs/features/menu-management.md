# Menu Management

*Phase 1 — shipped.*

## What it does

Your menu is the foundation OpsMind builds everything else on. You record each
dish with its price and (optionally) its ingredient cost, group dishes into
categories, and hide items you're not serving right now. Accurate prices and
costs are what let the AI calculate profit margins and give pricing advice.

## How to use it

Open **Menu** in the sidebar.

- **Add item** — enter a name, pick a category, set the price, and optionally
  add ingredient costs. Prices are validated (no negative or non-numeric
  values).
- **Categories** — group dishes (e.g. Burgers, Drinks, Desserts) so reports and
  the menu list stay organized.
- **Availability** — mark an item **unavailable** instead of deleting it. This
  is ideal for seasonal or sold-out dishes: it disappears from active views but
  keeps its history and can be switched back on later.
- **Edit / remove** — update price, cost, category, or name any time; remove
  items you no longer serve.

> **Tip:** the more accurate your ingredient costs, the better the AI's margin
> and pricing recommendations.

## Who can use it

| Role | Menu access |
|------|-------------|
| **Owner** | View and edit everything |
| **Manager** | View and edit everything |
| **Staff** | View only |

Editing (add / update / delete) is restricted to **Owners and Managers**;
Staff can view the menu but not change it. This is enforced on the server, not
just hidden in the UI.

## Security notes

- Every menu item and category carries your `tenant_id`. You only ever see and
  edit **your own** restaurant's menu — never another restaurant's.
- Write access (create/update/delete) requires the Owner or Manager role,
  checked server-side on every request.
- See the full model in [Security](../security.md).

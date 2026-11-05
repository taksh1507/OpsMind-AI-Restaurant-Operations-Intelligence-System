# Step 7: global search

The command menu now uses the shared authenticated API client at `/search`,
which resolves beneath `NEXT_PUBLIC_API_URL` (normally `/api/v1`). The formerly
unused `useSearch` hook is used by the menu. It debounces for 250 ms, aborts
superseded requests, guards against late responses and cancels on close/unmount.
Errors are visible rather than appearing as successful empty results.

The backend applies tenant-scoped SQL substring filters before limiting results
to 20 per type. There is no first-50 scan or Python fuzzy matching. Names sort
case-insensitively with ID tie-breaking. `%`, `_` and backslashes are literal
search characters, not user-controlled SQL wildcards. Prices use INR; category
results no longer claim an invented item count. Count matches the returned
result length (up to 60).

Staff accounts see available menu items under active, owned categories and
active categories only. Managers/owners can also search archived menu records
and staff names/job roles; staff contact information, wages and notes are not
returned. Native PostgreSQL enum roles are cast to text before ILIKE.

The command menu preserves server matches instead of filtering them by numeric
IDs, uses distinct keys per result type and focuses the input on open. The
header search button works. Navigation actions and shortcuts respect the user's
role, and G-prefix shortcuts do not intercept typing in forms. Staff search
results show name/role information; they no longer link to unrelated Settings
or to team login accounts, which are a different entity.

## Verification

- SQLite: 15 search tests passed (32.53s).
- PostgreSQL 18.6: the same 15 tests passed (56.51s), using the isolated cluster
  on localhost port 55432 and temporary per-test schemas. Existing application
  databases were not changed.
- Tests cover the 60th menu/category/staff record for each of two tenants,
  filtering in SQL, 20-per-type limits, matching counts, INR prices, role
  restrictions, archived records, native enum roles, literal wildcard names,
  missing/invalid queries, authentication and safe database errors.
- TypeScript, targeted ESLint for `useSearch`, CommandMenu and Layout, scoped
  backend Flake8 F checks, `git diff --check`, and production Next.js build pass.
- Browser inventory is still empty; a visual command-menu check is pending.
  Existing repository-wide lint issues from later audit steps are unchanged.

Full repeated regression: **227 passed, two PostgreSQL-only checks skipped**
on both runs (130.54s and 112.66s). Artifact hashes and Git status were unchanged
after each run. All temporary PostgreSQL schemas were removed and the isolated
test cluster was stopped.

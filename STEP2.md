# Step 2 — dependency upgrades (20 October 2026)

The required production dependency audits, backend suite and frontend build pass.
Work remains on the existing frontend lint findings and an unpatched development
dependency advisory; neither is hidden or excluded from the full audit results.

## Changes

- Runtime requirements use exact pins, including FastAPI 0.151.0,
  python-multipart 0.0.32, Gunicorn 26.2.0, scikit-learn 1.9.1,
  python-dotenv 1.2.4 and Anthropic 1.15.0. Starlette resolves to 1.9.0.
- Replaced python-jose with PyJWT 2.15.1, retaining HS256 and refresh-token
  rejection at access-token validation. Added tests for expiration, wrong keys,
  incorrect algorithms and refresh-token uniqueness.
- Replaced passlib with direct argon2-cffi hashing. Existing Argon2 hashes and
  bcrypt hashes remain verifiable, including legacy bcrypt truncation behavior.
  New passwords use Argon2id without bcrypt's length limit. Invalid hashes fail
  closed. The seed script uses the same application password hasher.
- Moved development tools into `requirements-dev.txt`; CI and the development
  setup instructions now install that file. Docker retains runtime-only installs.
- Upgraded Next.js and eslint-config-next to 16.4.2 and applied `npm audit fix`.
  Axios resolves to 1.20.0 (also the new declared minimum), form-data 4.0.6,
  nanoid 3.3.20, PostCSS 8.5.23 and sharp 0.35.5. The lockfile is updated.
- Retrained the committed sentiment model using the new numerical stack:
  accuracy 0.8423, precision 0.8571, recall 0.8182, F1 0.8372. Reloading it
  produces predictions without scikit-learn version warnings.

## Verification

Used a fresh `.venv-step2` without system-site packages, installed directly from
`requirements-dev.txt`, on Windows/Python 3.14. Versions were selected using
official package metadata for Python 3.11 compatibility; Python 3.11 and Linux
runtime execution were not exercised locally.

| Check | Result |
| --- | --- |
| `python -m pip_audit -r requirements.txt --progress-spinner off` | No known vulnerabilities found, exit 0 |
| `npm audit --omit=dev --audit-level=high` | Zero vulnerabilities, exit 0 |
| `python -m pip check` | No broken requirements, exit 0 |
| `npm run build` | Production build passes, including TypeScript and static page generation |
| `python -m pytest -q` | 105 passed |
| `python scripts/verify_test_isolation.py` | 105 passed twice (116.07s and 98.14s); artifact hashes and Git status unchanged after each run |
| Flake8 F checks on security module and migration tests | Pass |
| `git diff --check` | Pass |

All three committed forecast pickles load and predict with XGBoost 3.2.0, so
they did not require retraining. Loading the first older forecast emits an
XGBoost serialized-model compatibility warning; the duplicate/stale baseline
model cleanup remains part of Step 13. Tests create their own models and do not
modify these committed artifacts.

## Remaining development checks

The full npm audit reports five high package entries from one development-only
chain: eslint-config-next → @next/eslint-plugin-next → fast-glob → micromatch →
braces. [GHSA-vfj7-8cjw-p6xm](https://github.com/advisories/GHSA-vfj7-8cjw-p6xm)
lists no patched braces version. npm proposes a breaking downgrade to
eslint-config-next 14.2.35; that downgrade was not applied. The required
production audit (`--omit=dev`) is clean; the complete development tree is not.

The upgraded ESLint config reports **21 errors and 7 warnings**, compared with
the earlier 12 errors and 6 warnings. Additional React hooks/ref diagnostics
are exposed by the newer rules. The production build passes. Frontend lint
cleanup remains in Steps 6 and 14; lint rules were not disabled.

Migration references: [PyJWT HS256 usage](https://pyjwt.readthedocs.io/en/stable/usage.html)
and [argon2-cffi API](https://argon2-cffi.readthedocs.io/en/stable/api.html).

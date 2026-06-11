# Orca v7 — Known Security Debts

Documented but **not implemented**. Do not fix unless explicitly requested.

---

## 1. Password security (P2)
**File:** `src/web/auth.py`, `src/web/templates/login.html`

**Current state (BAD):**
- Plaintext password compared with `password == _APP_PASSWORD`
- Password stored in config/env as plaintext, accessible to anyone with filesystem access
- Login form likely posts password via unencrypted HTTP
- No rate limiting or login delay
- Session tokens stored in memory only, no expiry, no rotation
- `.htpasswd` exists in repo but unused

**Why not fixing now:**
- Testing only, 1-3 users
- HTTPS is not set up; hashing without TLS doesn't significantly improve security
- Fixing requires coordinated change to API, templates, auth module, and env setup
- Will be addressed when we actually deploy publicly

**What the correct fix would be:**
1. Hash passwords with bcrypt/argon2, store only hashes in `.htpasswd`
2. Enforce HTTPS (Let's Encrypt or reverse-proxy TLS termination)
3. Add rate limiting (e.g., slow down after 5 failed attempts)
4. Add session expiry (e.g., 24h) + proper token format (JWT or signed cookies)
5. Never return the password hash from any API endpoint

---

## 2. No CORS policy (P3)
**File:** `src/web/api.py`

**Current state:**
- No CORS headers configured
- Browser requests from other origins will be blocked silently
- If we add a separate frontend domain, this will break

**Why not fixing now:**
- Monolithic Jinja2 app, everything is same-origin
- Will matter when web-app and API are served from different origins (e.g., CDN + API)

---

## 3. In-memory session state (P2)
**Files:** `src/web/session.py`, `src/web/wizard_state.py`

**Current state:**
- All sessions/wizard state stored in Python dict in memory
- Lost on restart, no persistence, no expiry, no cleanup for zombies
- Fine for 1-3 users during testing

**Why not fixing now:**
- SQLite/Redis adds operational complexity
- 1-3 users, 1-2x/day — memory is sufficient
- Will be addressed if we need persistence or scaling

---

## 4. No CSRF protection (P2)
**File:** `src/web/api.py`

**Current state:**
- No CSRF tokens on mutating endpoints
- A malicious site could trigger state-changing requests if the user is logged in

**Why not fixing now:**
- Same-origin architecture (Jinja2 serves both pages and API)
- Low risk for internal testing
- Will add CSRF tokens when adding cross-origin support

---

## 5. No input validation on wizard endpoints (P1)
**File:** `src/web/api_wizard.py`

**Current state:**
- Wizard state updates trust client-supplied data directly
- No length/type/range validation on wizard fields beyond what JavaScript does
- A crafted request could inject invalid data into the pipeline

**Why not fixing now:**
- Trusted users (1-3 testers), internal tool
- Fixed when we stabilize the wizard schema and add backend validation

---

## 6. Service worker cache poisoning risk (P3)
**File:** `src/web/static/service-worker.js`

**Current state:**
- Cache-first strategy for all static assets
- No version invalidation mechanism
- A stale/corrupted cache may persist indefinitely

**Why not fixing now:**
- Testing only, cache can be cleared manually if needed
- Will add `CACHE_VERSION` + cache busting when deploying

---

## 7. File upload lacks validation (P2)
**File:** `src/web/api.py`

**Current state:**
- Upload endpoint exists (`/upload`)
- No file type/size/content validation
- Could allow uploading malicious files

**Why not fixing now:**
- Internal users only
- Will add MIME type + size limits + virus scan when deploying publicly

---

## 8. Debug endpoints exposed in production (P3)
**File:** `src/web/api.py`

**Current state:**
- `/api/debug/{session_id}` available without auth gate in some cases
- `/api/sessions` lists all active sessions
- `/api/schedule/schema` exposes internal data model

**Why not fixing now:**
- Internal testing only
- Will gate these behind auth or disable in production build

---

## Priority Summary

| # | Debt | Severity | Effort to fix | Planned fix |
|---|------|----------|---------------|-------------|
| P1 | Wizard input validation | Medium | Medium | Before public deploy |
| P2 | Password hashing | High | Low | Before public deploy |
| P2 | Session expiry | Medium | Low | Before public deploy |
| P2 | File upload validation | Medium | Low | Before public deploy |
| P3 | CORS policy | Low | Low | When splitting origins |
| P3 | CSRF tokens | Low | Medium | When adding cross-origin |
| P3 | Service worker versioning | Low | Low | At deploy time |
| P3 | Debug endpoint gating | Low | Low | At deploy time |
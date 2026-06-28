# Fintech API — JWT Authentication System

Django REST Framework API with full JWT authentication, session tracking, custom auth backend, and security analysis.

---

## Deliverables

### 1. Full Auth System — register/login/logout/refresh/revoke with JWT

| # | File | What it contains |
|---|------|-----------------|
| 1 | [`authentication/views.py`](fintech_api/authentication/views.py) | `RegisterView`, `LoginView`, `LogoutView`, `TokenRefreshWithRotationView`, `TokenRevokeView` |
| 2 | [`authentication/serializers.py`](fintech_api/authentication/serializers.py) | `RegisterSerializer`, `LoginSerializer`, `CustomTokenObtainPairSerializer`, `TokenRefreshWithRotationSerializer`, `LogoutSerializer` |
| 3 | [`authentication/models.py`](fintech_api/authentication/models.py) | `BlacklistedToken` model — JTI blacklist for revoked tokens |
| 4 | [`authentication/urls.py`](fintech_api/authentication/urls.py) | 8 URL routes under `/api/auth/` |
| 5 | [`fintech_api/settings.py`](fintech_api/fintech_api/settings.py) | `SIMPLE_JWT` config: access 30min, refresh 7 days, rotation ON, blacklist ON |
| 6 | [`fintech_api/settings.py`](fintech_api/fintech_api/settings.py) | `REST_FRAMEWORK` config: JWT + Session + Basic auth side by side |

**Refresh token rotation + blacklisting:** Each refresh call blacklists the old JTI and issues a new pair. Reuse of blacklisted tokens is detected and rejected.

**Custom JWT claims:** `role`, `email`, `account_ids` injected into JWT payload.

---

### 2. Session Tracker — active sessions list + revoke endpoint

| # | File | What it contains |
|---|------|-----------------|
| 1 | [`authentication/models.py`](fintech_api/authentication/models.py) | `ActiveSession` model — stores device, IP, user_agent, JTI per token |
| 2 | [`authentication/views.py`](fintech_api/authentication/views.py) | `_get_client_ip()`, `_create_session()` helpers + `ActiveSessionsView` (GET list, DELETE by ID, DELETE all) |

---

### 3. Custom Auth Backend — email-based login instead of username

| # | File | What it contains |
|---|------|-----------------|
| 1 | [`authentication/auth_backends.py`](fintech_api/authentication/auth_backends.py) | `EmailAuthBackend` — authenticate by email OR username |
| 2 | [`fintech_api/settings.py`](fintech_api/fintech_api/settings.py) | `AUTHENTICATION_BACKENDS` — EmailAuthBackend first, ModelBackend fallback |

---

### 4. Security Write-Up — 1-page JWT threat analysis

| # | File | What it contains |
|---|------|-----------------|
| 1 | [`authentication/SECURITY_ANALYSIS.md`](fintech_api/authentication/SECURITY_ANALYSIS.md) | 7 threat analyses + 2 simulated vulnerabilities with fixes |

**2 vulnerabilities simulated & fixed:**
1. **User enumeration via verbose errors** — fixed with generic `"Invalid credentials"` response
2. **Refresh token reuse attack** — fixed with rotation + blacklisting

---

## Tasks

### Task 1: DRF auth + SimpleJWT docs. Token auth + JWT side by side
- **DRF authentication classes** in `settings.py` — `JWTAuthentication`, `SessionAuthentication`, `BasicAuthentication` all enabled
- **SimpleJWT config** in `settings.py` — access token lifetime, refresh lifetime, rotation, blacklisting
- **Postman comparison** at [`Fintech.postman_collection.json`](Fintech.postman_collection.json) — 3 folders:
  - `1. JWT Auth Flow` — register, login, refresh, sessions, logout
  - `2. COMPARE: Basic Auth (Token) — CRUD` — accounts/transactions via Basic auth (username:password header)
  - `3. COMPARE: JWT Bearer Auth — Same CRUD` — same endpoints via JWT Bearer token header
- **Key difference:** Basic Auth sends credentials on every request (stateless, no session). JWT sends a signed token — supports refresh rotation, blacklisting, custom payload claims, and session tracking.

### Task 2: Register, Login, Logout with JWT. Refresh token rotation + blacklisting
- **Register** → [`authentication/views.py`](fintech_api/authentication/views.py) — creates user + issues JWT pair + creates ActiveSession
- **Login** → [`authentication/views.py`](fintech_api/authentication/views.py) — authenticates via email/password → JWT pair + session
- **Logout** → [`authentication/views.py`](fintech_api/authentication/views.py) — blacklists JTI + deactivates session + ownership check
- **Refresh rotation** → [`authentication/serializers.py`](fintech_api/authentication/serializers.py) — blacklists old JTI, issues new pair, updates session JTI
- **Blacklisting** → [`authentication/models.py`](fintech_api/authentication/models.py) — `BlacklistedToken` model with `is_blacklisted()` classmethod

### Task 3: Custom JWT claims + email-based auth backend
- **Custom claims** → [`authentication/serializers.py`](fintech_api/authentication/serializers.py) — `CustomTokenObtainPairSerializer` adds `role`, `email`, `account_ids`
- **Email auth backend** → [`authentication/auth_backends.py`](fintech_api/authentication/auth_backends.py) — `EmailAuthBackend` authenticates via email or username

### Task 4: Session tracking + list/revoke endpoints
- **ActiveSession model** → [`authentication/models.py`](fintech_api/authentication/models.py) — tracks device, IP, user_agent, JTI, timestamps
- **Session creation** → [`authentication/views.py`](fintech_api/authentication/views.py) — `_create_session()` on every login/register
- **List/revoke** → [`authentication/views.py`](fintech_api/authentication/views.py) — `ActiveSessionsView`: GET lists all, DELETE revokes

### Task 5: Security analysis — JWT threats + simulate/fix 2 vulnerabilities
- **Security analysis** → [`authentication/SECURITY_ANALYSIS.md`](fintech_api/authentication/SECURITY_ANALYSIS.md)
- Covers: Token leakage, expiry windows, signing key rotation, no built-in revocation, user enumeration, refresh token reuse, algorithm confusion
- **Vuln 1 fix**: Generic `"Invalid credentials"` error for all auth failures
- **Vuln 2 fix**: Refresh rotation + blacklist to prevent reuse attacks

---




## Auth Endpoints

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/api/auth/register/` | No | Register → JWT pair + session |
| POST | `/api/auth/login/` | No | Login (email/username) → JWT pair + session |
| POST | `/api/auth/logout/` | Bearer | Blacklists token, deactivates session |
| POST | `/api/auth/refresh/` | No | Rotates refresh token, issues new pair |
| POST | `/api/auth/revoke/` | Bearer | Explicitly revoke a refresh token |
| GET | `/api/auth/sessions/` | Bearer | List active sessions |
| DELETE | `/api/auth/sessions/<id>/` | Bearer | Revoke specific session |
| DELETE | `/api/auth/sessions/` | Bearer | Revoke all sessions |

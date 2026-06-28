# JWT Security Threat Analysis

## 1. JWT Threat Landscape

### 1.1 Token Leakage
**Risk:** JWTs can be intercepted via MitM, XSS, or client-side logging.
**Impact:** Full account takeover — access token grants API access; refresh token grants indefinite session renewal.

**Simulated in code:** An attacker who intercepts a refresh token can use it at `/api/auth/refresh/` to get new access tokens.

**Fix applied:** Refresh token rotation + blacklisting (`serializers.py:TokenRefreshWithRotationSerializer`). Each refresh
invalidates the previous token. If an attacker uses a stolen token after the legitimate user refreshes, it is detected as
reuse and both the old and new sessions are revoked:
```python
if BlacklistedToken.is_blacklisted(jti):
    BlacklistedToken.objects.filter(jti=jti).delete()
    ActiveSession.objects.filter(jti=jti).update(is_active=False)
    raise ValidationError('Token reuse detected.')
```

### 1.2 Token Expiry & Window of Attack
**Risk:** Long-lived tokens increase the damage window if leaked.
**Impact:** A 30-day refresh token gives an attacker 30 days of access.

**Fix applied:** Short access token lifetime (30 min) + 7-day refresh token (`settings.py`):
```python
'ACCESS_TOKEN_LIFETIME': timedelta(minutes=30),
'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
```

### 1.3 Signing Key Rotation
**Risk:** If the SECRET_KEY is compromised, all tokens (past and future) can be forged.
**Impact:** Complete system compromise — arbitrary user impersonation.

**Mitigation (operational):** Store SECRET_KEY in environment variables / vault. Rotate keys periodically. Use
`SIMPLE_JWT['VERIFYING_KEY']` to support key rotation. Old tokens signed with previous key will be rejected after
rotation.

### 1.4 No Built-in Revocation
**Risk:** JWTs are stateless — there is no server-side session to invalidate. Once issued, they are valid until expiry.
**Impact:** A logged-out user's token can still be used.

**Fix applied:** Token blacklisting via `BlacklistedToken` model (`models.py`). All revocation paths (logout, revoke,
session kill) insert the token's `jti` into the blacklist. A database lookup on refresh verifies the token hasn't been
revoked:
```python
@classmethod
def is_blacklisted(cls, jti):
    return cls.objects.filter(jti=jti, expires_at__gt=timezone.now()).exists()
```

### 1.5 User Enumeration via Login Endpoint
**Risk:** Different error messages for "user not found" vs "wrong password" allow attackers to enumerate valid emails.
**Impact:** Targeted credential stuffing or phishing attacks.

**Fix applied:** Uniform "Invalid credentials" response for both cases (`serializers.py:LoginSerializer`):
```python
if not user:
    raise ValidationError('Invalid credentials.', code='authorization')
```

### 1.6 Refresh Token Reuse
**Risk:** Without rotation, a stolen refresh token can be used indefinitely.
**Impact:** Persistent unauthorized access.

**Fix applied:** Rotation + blacklisting. Each `/api/auth/refresh/` call invalidates the old token and issues a new one.
If the old token is reused, both old and new tokens are blacklisted, and all user sessions are force-logged-out.

### 1.7 JWK Injection / Algorithm Confusion
**Risk:** Attackers can change the JWT `alg` header from `RS256` to `HS256` and sign with the public key (if known).
**Impact:** Token forgery.

**Fix applied:** SimpleJWT defaults to `HS256` with a server-side secret. For production, pin the algorithm:
```python
SIMPLE_JWT = {
    'ALGORITHM': 'HS256',
    # or for RS256:
    # 'ALGORITHM': 'RS256',
    # 'VERIFYING_KEY': PUBLIC_KEY,
}
```

---

## 2. Vulnerabilities Simulated & Fixed

### Vulnerability 1: Verbose Error Messages (User Enumeration)

**Before (vulnerable):** The login endpoint would reveal whether an email exists:
```
{"email": ["User with this email does not exist."]}   # vs
{"password": ["Wrong password."]}
```

**Exploitation:** An attacker iterates emails, observes different responses for valid vs invalid emails, builds a target
list for phishing.

**Fix:** Single generic error for all authentication failures (`authentication/serializers.py:54-59`):
```
{"non_field_errors": ["Invalid credentials."]}
```

**Verification:** Tests 5 & 6 confirm identical responses for wrong-password and non-existent-email cases.

### Vulnerability 2: Missing Refresh Token Rotation (Reuse Attack)

**Before (vulnerable):** Refresh tokens never changed. A leaked token worked until expiry.

**Exploitation:** Attacker steals refresh token → calls `/api/auth/refresh/` → gets new access token → repeats until
refresh token expires (potentially 30 days).

**Fix:** Custom `TokenRefreshWithRotationSerializer` (`authentication/serializers.py:101-145`):
1. Validates old token
2. Checks blacklist for reuse
3. Blacklists old token
4. Issues new token pair
5. Updates session with new jti
6. On reuse detection: blacklists all tokens for that jti, revokes session

**Verification:** Tests 3 & 4 show:
- First refresh returns new tokens (status 200)
- Second reuse of same token is rejected as "token reuse detected" (status 400)

---

## 3. Security Recommendations

| Threat | Mitigation | Status |
|--------|-----------|--------|
| Token leakage | Short TTL + rotation | ✅ Implemented |
| No revocation | Blacklist model (jti) | ✅ Implemented |
| Reuse attack | Rotation + blacklist | ✅ Implemented |
| Email enumeration | Generic error messages | ✅ Implemented |
| Algorithm confusion | Pin algorithm in settings | ✅ Configured |
| CSRF (non-browser) | Token in Auth header, not cookie | ✅ N/A (Bearer auth) |
| Weak secret | Environment-based SECRET_KEY | 🔧 Production setup |
| Key rotation | Versioned keys | 🔧 Manual process |
| Rate limiting | Per-IP throttling on auth endpoints | 🔧 Add with DRF throttling |
| Audit logging | Log all auth events | 🔧 Add structured logging |

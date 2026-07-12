# Permission Matrix — Fintech API

## Role Definitions

| Role | JWT `role` claim | How Assigned |
|------|-----------------|--------------|
| **Admin** | `admin` | `User.is_superuser=True` or `Role.role='admin'` |
| **Agent** | `agent` | `Role.role='agent'` (staff handling support) |
| **Customer** | `customer` | Default for all non-admin/non-agent users |

Roles are stored in the `Role` model (`authentication.models.Role`) and embedded in the JWT access token via the `role` claim.

---

## Endpoint x Role Matrix

### Authentication Endpoints

| Endpoint | Method | Admin | Agent | Customer | Anonymous | Permission Class |
|----------|--------|-------|-------|----------|-----------|-----------------|
| `POST /api/auth/register/` | POST | Allowed | Allowed | Allowed | Allowed | `AllowAny` |
| `POST /api/auth/login/` | POST | Allowed | Allowed | Allowed | Allowed | `AllowAny` |
| `POST /api/auth/logout/` | POST | Allowed | Allowed | Allowed | Denied | `IsAuthenticated` |
| `POST /api/auth/refresh/` | POST | Allowed | Allowed | Allowed | Allowed | `AllowAny` |
| `POST /api/auth/revoke/` | POST | Allowed | Allowed | Allowed | Denied | `IsAuthenticated` |
| `GET /api/auth/sessions/` | GET | Allowed (own) | Allowed (own) | Allowed (own) | Denied | `IsAuthenticated` |
| `DELETE /api/auth/sessions/` | DELETE | Allowed (own) | Allowed (own) | Allowed (own) | Denied | `IsAuthenticated` |
| `DELETE /api/auth/sessions/<id>/` | DELETE | Allowed (own) | Allowed (own) | Allowed (own) | Denied | `IsAuthenticated` |

### Account Endpoints

| Endpoint | Method | Admin | Agent | Customer | Permission Class |
|----------|--------|-------|-------|----------|-----------------|
| `GET /api/accounts/` | GET | Allowed (all) | Allowed (all) | Allowed (own) | `IsAuthenticated` |
| `POST /api/accounts/` | POST | Allowed | Allowed | Allowed | `IsAuthenticated` |
| `GET /api/accounts/<id>/` | GET | Allowed | Allowed | Allowed (own) | `IsAccountOwnerOrAdmin` |
| `PUT /api/accounts/<id>/` | PUT | Allowed | Denied | Allowed (own) | `IsAccountOwnerOrAdmin` |
| `PATCH /api/accounts/<id>/` | PATCH | Allowed | Denied | Allowed (own) | `IsAccountOwnerOrAdmin` |
| `DELETE /api/accounts/<id>/` | DELETE | Allowed | Denied | Allowed (own) | `IsAccountOwnerOrAdmin` |
| `POST /api/accounts/<id>/freeze/` | POST | Allowed | Allowed | Denied | `IsAdmin \| IsAgent` |
| `GET /api/accounts/<id>/statement/` | GET | Allowed | Allowed | Allowed (own) | `IsAccountOwnerOrAdmin` |

### Transaction Endpoints

| Endpoint | Method | Admin | Agent | Customer | Permission Class |
|----------|--------|-------|-------|----------|-----------------|
| `GET /api/transactions/` | GET | Allowed (all) | Allowed (customer txns) | Allowed (own) | `IsOwnerOrReadOnly` |
| `POST /api/transactions/` | POST | Allowed | Allowed | Allowed (own) | `IsOwnerOrReadOnly` |
| `GET /api/transactions/<id>/` | GET | Allowed | Allowed (customer txns) | Allowed (own) | `IsOwnerOrReadOnly` |
| `PUT /api/transactions/<id>/` | PUT | Allowed | Denied | Allowed (own) | `IsOwnerOrReadOnly` |
| `PATCH /api/transactions/<id>/` | PATCH | Allowed | Denied | Allowed (own) | `IsOwnerOrReadOnly` |
| `DELETE /api/transactions/<id>/` | DELETE | Allowed | Denied | Allowed (own) | `IsOwnerOrReadOnly` |
| `POST /api/transactions/<id>/reverse/` | POST | Allowed | Denied | Allowed (own) | `IsOwnerOrReadOnly` |

### Comparison Endpoints (unchanged)

| Endpoint | Method | Admin | Agent | Customer | Anonymous | Permission Class |
|----------|--------|-------|-------|----------|-----------|-----------------|
| `GET /api-compare/accounts-api/` | GET | Allowed | Allowed | Allowed | Denied | `IsAuthenticated` |
| `POST /api-compare/accounts-api/` | POST | Allowed | Allowed | Allowed | Denied | `IsAuthenticated` |
| `GET /api-compare/accounts-generic/` | GET | Allowed | Allowed | Allowed | Allowed | `IsAuthenticatedOrReadOnly` |
| `POST /api-compare/accounts-generic/` | POST | Allowed | Allowed | Allowed | Denied | `IsAuthenticatedOrReadOnly` |

---

## Break Attempts — curl Commands

Below are curl commands to attempt breaking the permission system. All should return `403 Forbidden`.

### 1. Customer trying to freeze another customer's account

```bash
# Login as customer1
ACCESS=$(curl -s -X POST http://127.0.0.1:8000/api/auth/login/ \
  -H 'Content-Type: application/json' \
  -d '{"email":"customer1@test.com","password":"pass1234"}' | python3 -c "import sys,json; print(json.load(sys.stdin)['access'])")

# Try to freeze account 2 (owned by customer2)
curl -s -X POST http://127.0.0.1:8000/api/accounts/2/freeze/ \
  -H "Authorization: Bearer $ACCESS" \
  -H 'Content-Type: application/json' \
  -d '{"reason":"test"}'
# Expected: 403 Forbidden
```

### 2. Agent trying to edit (PUT) an account

```bash
ACCESS=$(curl -s -X POST http://127.0.0.1:8000/api/auth/login/ \
  -H 'Content-Type: application/json' \
  -d '{"email":"agent@test.com","password":"pass1234"}' | python3 -c "import sys,json; print(json.load(sys.stdin)['access'])")

curl -s -X PUT http://127.0.0.1:8000/api/accounts/1/ \
  -H "Authorization: Bearer $ACCESS" \
  -H 'Content-Type: application/json' \
  -d '{"account_number":"HACKED","account_type":"BUSINESS"}'
# Expected: 403 Forbidden
```

### 3. Unauthenticated access to protected endpoints

```bash
curl -s http://127.0.0.1:8000/api/accounts/
# Expected: 401 Unauthorized

curl -s http://127.0.0.1:8000/api/transactions/
# Expected: 401 Unauthorized
```

### 4. Customer trying to access another customer's transactions

```bash
ACCESS=$(curl -s -X POST http://127.0.0.1:8000/api/auth/login/ \
  -H 'Content-Type: application/json' \
  -d '{"email":"customer1@test.com","password":"pass1234"}' | python3 -c "import sys,json; print(json.load(sys.stdin)['access'])")

# Try to view transaction owned by customer2
curl -s http://127.0.0.1:8000/api/transactions/5/ \
  -H "Authorization: Bearer $ACCESS"
# Expected: 404 Not Found (filtered out of queryset) or 403 Forbidden
```

### 5. Customer trying to reverse another customer's transaction

```bash
ACCESS=$(curl -s -X POST http://127.0.0.1:8000/api/auth/login/ \
  -H 'Content-Type: application/json' \
  -d '{"email":"customer1@test.com","password":"pass1234"}' | python3 -c "import sys,json; print(json.load(sys.stdin)['access'])")

curl -s -X POST http://127.0.0.1:8000/api/transactions/5/reverse/ \
  -H "Authorization: Bearer $ACCESS" \
  -H 'Content-Type: application/json' \
  -d '{"reason":"fraud"}'
# Expected: 404 or 403
```

### 6. Agent trying to delete an account

```bash
ACCESS=$(curl -s -X POST http://127.0.0.1:8000/api/auth/login/ \
  -H 'Content-Type: application/json' \
  -d '{"email":"agent@test.com","password":"pass1234"}' | python3 -c "import sys,json; print(json.load(sys.stdin)['access'])")

curl -s -X DELETE http://127.0.0.1:8000/api/accounts/1/ \
  -H "Authorization: Bearer $ACCESS"
# Expected: 403 Forbidden
```

---

## django-guardian Usage

Object-level permissions are granted via `assign_perm` in `TransactionViewSet.perform_create`:

```python
from guardian.shortcuts import assign_perm

# After creating a transaction, grant the owner view + change perms
assign_perm('view_transaction', account.user, txn)
assign_perm('change_transaction', account.user, txn)
```

This enables per-object lookups:

```python
from guardian.shortcuts import get_objects_for_user

# Get all transactions a user has explicit permission to view
user_txns = get_objects_for_user(user, 'accounts.view_transaction')
```

Guardian's `ObjectPermissionBackend` is registered in `AUTHENTICATION_BACKENDS` to
support `user.has_perm('accounts.change_transaction', specific_txn)`.

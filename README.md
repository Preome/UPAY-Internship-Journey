# Fintech API — DRF Permissions & RBAC System

Django REST Framework API with JWT authentication, custom permission classes, role-based access control (RBAC), object-level row security, and django-guardian per-object permissions.

---

## Deliverables

| # | Deliverable | Status |
|---|-------------|--------|
| 1 | Custom permission classes — 8 reusable classes   | [`accounts/permissions.py`](fintech_api/accounts/permissions.py)|
| 2 | RBAC system — Admin, Agent, Customer roles with enforced endpoint access via JWT claims | [`accounts/permissions.py`](fintech_api/accounts/permissions.py), [`authentication/models.py`](fintech_api/authentication/models.py) |
| 3 | Row-level security — users scoped to their own Transactions and Accounts only | [`accounts/views.py`](fintech_api/accounts/views.py) |
| 4 | Permission matrix — full endpoint x role table  |  
[`PERMISSION_MATRIX.md`](fintech_api/PERMISSION_MATRIX.md)
---

## Task 1: Built-in DRF Permissions + django-guardian

### Built-in permission classes used

| Permission | Description | Where used |
|------------|-------------|------------|
| `IsAuthenticated` | Only authenticated users may access | Global default in [`settings.py:138`](fintech_api/fintech_api/settings.py#L138), [`AccountAPIView:45`](fintech_api/accounts/views.py#L45), [`AccountViewSet:98-100`](fintech_api/accounts/views.py#L98), [`LogoutView:111`](fintech_api/authentication/views.py#L111) |
| `IsAdminUser` | Only `is_staff=True` users | Not used directly — replaced by custom `IsAdmin` RBAC class |
| `IsAuthenticatedOrReadOnly` | Safe methods: anyone; mutating methods: authenticated only | [`AccountGenericView:72`](fintech_api/accounts/views.py#L72) |
| `AllowAny` | No authentication required | [`RegisterView:45`](fintech_api/authentication/views.py#L45), [`LoginView:75`](fintech_api/authentication/views.py#L75), [`TokenRefreshWithRotationView:142`](fintech_api/authentication/views.py#L142) |

**Built-in vs Custom:** The built-in `IsAdminUser` checks `is_staff` on the Django `User` model but has no concept of JWT role claims. The custom `IsAdmin` class reads the `role` claim from the decoded JWT, making it suitable for token-based RBAC. `IsAuthenticatedOrReadOnly` is used on the comparison endpoint to demonstrate DRF's read-open/write-closed pattern.

### django-guardian integration

django-guardian adds **per-object permission lookups** — you can check if a user has `view_transaction` on a *specific* Transaction instance, not just the model-level permission.

**Setup:**

| File | Change |
|------|--------|
| [`settings.py:35`](fintech_api/fintech_api/settings.py#L35) | `'guardian'` added to `INSTALLED_APPS` |
| [`settings.py:89`](fintech_api/fintech_api/settings.py#L89) | `'guardian.backends.ObjectPermissionBackend'` added to `AUTHENTICATION_BACKENDS` |

**Usage in [`TransactionViewSet.perform_create`](fintech_api/accounts/views.py#L196):**

```python
from guardian.shortcuts import assign_perm

txn = serializer.save(reference_number=reference, status='COMPLETED')
assign_perm('view_transaction', account.user, txn)
assign_perm('change_transaction', account.user, txn)
```

After a transaction is created, the owner gets explicit `view` and `change` permissions on that single row. This enables fine-grained lookups:

```python
from guardian.shortcuts import get_objects_for_user

# Only transactions the user has explicit permission to view
user_txns = get_objects_for_user(user, 'accounts.view_transaction')
```

Guardian also supports deny-logic and group-based permissions, but this project uses the user-level `assign_perm` pattern for simplicity.

---

## Task 2: Custom Permission Classes — AND/OR Composition

All custom permissions live in [`accounts/permissions.py`](fintech_api/accounts/permissions.py).

### Permission class inventory

| Class | Type | Purpose |
|-------|------|---------|
| `CombinablePermission` | Base | Base class for all custom permissions |
| `And(*perms)` | Combinator | All child permissions must pass |
| `Or(*perms)` | Combinator | At least one child permission must pass |
| `IsAccountOwner` | Object-level | User owns the target Account or Transaction |
| `IsVerifiedUser` | View-level | User has a non-empty email address |
| `IsActiveAccount` | Object-level | Target account is not frozen |
| `IsAccountOwnerOrAdmin` | Object-level | Owner OR `is_staff`/`is_superuser` |
| `HasRole(*roles)` | View-level | Reads `role` claim from JWT; accepts any of the listed roles |
| `IsAdmin` | View-level | Shortcut for `HasRole('admin')` |
| `IsAgent` | View-level | Shortcut for `HasRole('agent')` |
| `IsCustomer` | View-level | Shortcut for `HasRole('customer')` |
| `IsOwnerOrReadOnly` | Object-level | Read: any auth user; mutate: owner or admin only |
| `IsOwnerReadOnlyOrAdmin` | Object-level | Read: owner only; mutate: owner or admin |

### AND/OR composition

The `And` and `Or` classes accept any permission instances and compose them:

```python
from accounts.permissions import And, Or, IsVerifiedUser, IsActiveAccount, IsAdmin, IsAgent

# Both must pass
permission_classes = [And(IsVerifiedUser(), IsActiveAccount())]

# At least one must pass
permission_classes = [Or(IsAdmin(), IsAgent())]
```

DRF's `BasePermission` metaclass also overloads `&` and `|` on **class objects**:

```python
permission_classes = [IsAdmin | IsAgent]   # same as Or(IsAdmin, IsAgent) at class level
```

The `And`/`Or` helpers work on **instances** and call `has_permission` + `has_object_permission` on each child, short-circuiting appropriately (`all()` for And, `any()` for Or).

**Real usage in [`AccountViewSet.get_permissions`](fintech_api/accounts/views.py#L98):**

```python
def get_permissions(self):
    if self.action in ('list', 'create'):
        return [IsAuthenticated()]
    if self.action == 'freeze':
        return [IsAdmin() | IsAgent()]          # DRF metaclass OR
    if self.action in ('retrieve', 'statement'):
        return [IsAccountOwnerOrAdmin()]
    return [IsAccountOwnerOrAdmin()]            # update / destroy
```

---

## Task 3: Role-Based Access Control (RBAC)

### Three roles

| Role | JWT `role` claim | How assigned |
|------|-----------------|--------------|
| **Admin** | `admin` | `User.is_superuser=True` or `Role.role='admin'` |
| **Agent** | `agent` | `Role.role='agent'` (support staff) |
| **Customer** | `customer` | Default for all non-admin/non-agent users |

### Role model

Defined in [`authentication/models.py:39`](fintech_api/authentication/models.py#L39):

```python
class Role(models.Model):
    ADMIN = 'admin'
    AGENT = 'agent'
    CUSTOMER = 'customer'

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='role_profile')
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default=CUSTOMER)
```

The `get_role_for_user()` classmethod checks `is_superuser` first (always returns `admin`), then falls back to the `Role` profile, defaulting to `customer`.

### JWT claim injection

In [`CustomTokenObtainPairSerializer.get_token`](fintech_api/authentication/serializers.py#L72):

```python
token['role'] = Role.get_role_for_user(user)
token['email'] = user.email
token['account_ids'] = list(Account.objects.filter(user=user).values_list('id', flat=True))
```

When a user logs in or registers, the access token carries the `role` claim. The `HasRole` permission class reads it from `request.auth['role']` at enforcement time.

### Enforcement in views

The `HasRole` base class (and its shortcuts `IsAdmin`, `IsAgent`, `IsCustomer`) check the JWT role claim:

```python
class HasRole(CombinablePermission):
    def has_permission(self, request, view):
        role = getattr(request, 'auth', None)       # decoded JWT payload
        token_role = role.get('role', '') if hasattr(role, 'get') else ''
        return token_role in self.allowed_roles
```

**Endpoint access enforcement:**

| Action | AccountViewSet | TransactionViewSet |
|--------|---------------|-------------------|
| list, create | `IsAuthenticated` (all roles) | `IsOwnerOrReadOnly` (owner scoped) |
| retrieve, update, destroy | `IsAccountOwnerOrAdmin` | `IsOwnerOrReadOnly` (object check) |
| freeze | `IsAdmin \| IsAgent` | — |
| reverse | — | `IsOwnerOrReadOnly` |

---

## Task 4: Object-Level Row Security

### Layer 1: queryset filtering

`get_queryset()` scopes the data before the object is ever fetched. Customers never see other users' records at the database level.

[`AccountViewSet.get_queryset`](fintech_api/accounts/views.py#L108):

```python
def get_queryset(self):
    user = self.request.user
    if user.is_staff or user.is_superuser:
        return Account.objects.all()        # admin sees everything
    return Account.objects.filter(user=user) # customer sees own only
```

[`TransactionViewSet.get_queryset`](fintech_api/accounts/views.py#L178):

```python
def get_queryset(self):
    user = self.request.user
    if user.is_staff or user.is_superuser:
        return Transaction.objects.all()
    qs = Transaction.objects.filter(account__user=user)
    # agents can also see customer transactions via guardian perms
    return qs.distinct()
```

### Layer 2: `get_object()` + `check_object_permissions()`

[`TransactionViewSet.get_object`](fintech_api/accounts/views.py#L191) overrides the default to enforce object-level checks on every detail request:

```python
def get_object(self):
    obj = super().get_object()                            # fetches from filtered queryset
    self.check_object_permissions(self.request, obj)      # runs IsOwnerOrReadOnly
    return obj
```

This ensures that even if a user crafts a URL with someone else's transaction ID, the `IsOwnerOrReadOnly.has_object_permission()` check blocks access at the object level — a second layer of defense beyond queryset filtering.

### Layer 3: django-guardian per-object grants

On transaction create, `assign_perm` grants the owner explicit row-level permissions:

```python
assign_perm('view_transaction', account.user, txn)
assign_perm('change_transaction', account.user, txn)
```

This enables scenarios where an agent needs temporary access to a specific customer transaction — call `assign_perm('view_transaction', agent_user, txn)` and the agent can now pass `user.has_perm('accounts.view_transaction', txn)`.

---

## Task 5: Permission Matrix

### Condensed matrix

| Endpoint | Method | Admin | Agent | Customer | Permission Class |
|----------|--------|-------|-------|----------|-----------------|
| `POST /api/auth/register/` | POST | Y | Y | Y | `AllowAny` |
| `POST /api/auth/login/` | POST | Y | Y | Y | `AllowAny` |
| `POST /api/auth/logout/` | POST | Y | Y | Y | `IsAuthenticated` |
| `POST /api/auth/refresh/` | POST | Y | Y | Y | `AllowAny` |
| `GET /api/accounts/` | GET | all | all | own | `IsAuthenticated` |
| `POST /api/accounts/` | POST | Y | Y | Y | `IsAuthenticated` |
| `GET /api/accounts/<id>/` | GET | Y | Y | owner | `IsAccountOwnerOrAdmin` |
| `PUT/PATCH /api/accounts/<id>/` | PUT | Y | denied | owner | `IsAccountOwnerOrAdmin` |
| `DELETE /api/accounts/<id>/` | DELETE | Y | denied | owner | `IsAccountOwnerOrAdmin` |
| `POST /api/accounts/<id>/freeze/` | POST | Y | Y | denied | `IsAdmin \| IsAgent` |
| `GET /api/accounts/<id>/statement/` | GET | Y | Y | owner | `IsAccountOwnerOrAdmin` |
| `GET /api/transactions/` | GET | all | customer txns | own | `IsOwnerOrReadOnly` |
| `POST /api/transactions/` | POST | Y | Y | own | `IsOwnerOrReadOnly` |
| `GET/PUT/DELETE /api/transactions/<id>/` | ALL | Y | read-only | owner | `IsOwnerOrReadOnly` |
| `POST /api/transactions/<id>/reverse/` | POST | Y | denied | owner | `IsOwnerOrReadOnly` |

Full matrix with all HTTP methods, anonymous access, and comparison endpoints: [`PERMISSION_MATRIX.md`](fintech_api/PERMISSION_MATRIX.md)

### Break attempts — curl commands

These commands attempt to bypass the permission system. All should fail with `401 Unauthorized` or `403 Forbidden`.

**1. Customer trying to freeze another customer's account:**

```bash
ACCESS=$(curl -s -X POST http://127.0.0.1:8000/api/auth/login/ \
  -H 'Content-Type: application/json' \
  -d '{"email":"customer1@test.com","password":"pass1234"}' | python3 -c "import sys,json; print(json.load(sys.stdin)['access'])")

curl -s -X POST http://127.0.0.1:8000/api/accounts/2/freeze/ \
  -H "Authorization: Bearer $ACCESS" \
  -H 'Content-Type: application/json' \
  -d '{"reason":"test"}'
# Expected: 403 Forbidden (IsAdmin | IsAgent required)
```

**2. Agent trying to edit (PUT) an account:**

```bash
ACCESS=$(curl -s -X POST http://127.0.0.1:8000/api/auth/login/ \
  -H 'Content-Type: application/json' \
  -d '{"email":"agent@test.com","password":"pass1234"}' | python3 -c "import sys,json; print(json.load(sys.stdin)['access'])")

curl -s -X PUT http://127.0.0.1:8000/api/accounts/1/ \
  -H "Authorization: Bearer $ACCESS" \
  -H 'Content-Type: application/json' \
  -d '{"account_number":"HACKED","account_type":"BUSINESS"}'
# Expected: 403 Forbidden (IsAccountOwnerOrAdmin — agent is not owner)
```

**3. Unauthenticated access to protected endpoints:**

```bash
curl -s http://127.0.0.1:8000/api/accounts/
# Expected: 401 Unauthorized

curl -s http://127.0.0.1:8000/api/transactions/
# Expected: 401 Unauthorized
```

**4. Customer trying to access another customer's transactions:**

```bash
ACCESS=$(curl -s -X POST http://127.0.0.1:8000/api/auth/login/ \
  -H 'Content-Type: application/json' \
  -d '{"email":"customer1@test.com","password":"pass1234"}' | python3 -c "import sys,json; print(json.load(sys.stdin)['access'])")

curl -s http://127.0.0.1:8000/api/transactions/5/ \
  -H "Authorization: Bearer $ACCESS"
# Expected: 404 (filtered out of queryset) or 403
```

**5. Customer trying to reverse another customer's transaction:**

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

**6. Agent trying to delete an account:**

```bash
ACCESS=$(curl -s -X POST http://127.0.0.1:8000/api/auth/login/ \
  -H 'Content-Type: application/json' \
  -d '{"email":"agent@test.com","password":"pass1234"}' | python3 -c "import sys,json; print(json.load(sys.stdin)['access'])")

curl -s -X DELETE http://127.0.0.1:8000/api/accounts/1/ \
  -H "Authorization: Bearer $ACCESS"
# Expected: 403 Forbidden (IsAccountOwnerOrAdmin — agent is not owner)
```

---

## Running the Tests

```bash
cd fintech_api
python3 manage.py shell < test_permissions.py
```

The script creates 4 test users (admin, agent, customer1, customer2), assigns roles, creates accounts and transactions, then exercises every permission class. Expected output:

```
TOTAL: 35  |  PASSED: 35  |  FAILED: 0
```

Tests cover:
- `And` / `Or` combinators
- `IsAccountOwner`, `IsVerifiedUser`, `IsActiveAccount`
- `IsAccountOwnerOrAdmin`
- `IsAdmin`, `IsAgent`, `IsCustomer` (RBAC via JWT role claim)
- `IsOwnerOrReadOnly`, `IsOwnerReadOnlyOrAdmin` (row-level security)
- django-guardian `assign_perm` / `has_perm` integration

---

## Project Structure

```
fintech_api/
  fintech_api/
    settings.py                  # guardian INSTALLED_APPS, AUTHENTICATION_BACKENDS
  accounts/
    models.py                    # Account, Transaction
    serializers.py               # AccountListSerializer, TransactionSerializer
    permissions.py               # NEW — 8 custom permission classes + And/Or combinators
    views.py                     # UPDATED — get_permissions(), get_queryset(), get_object()
    urls.py
  authentication/
    models.py                    # UPDATED — Role model (Admin/Agent/Customer)
    serializers.py               # UPDATED — JWT role claim from Role model
    views.py                     # Register/Login/Logout/Refresh/Revoke/Sessions
    urls.py
    auth_backends.py             # EmailAuthBackend
  test_permissions.py            # NEW — 35 automated permission tests
  PERMISSION_MATRIX.md           # NEW — full endpoint x role matrix + curl break scripts
  requirements.txt               # UPDATED — django-guardian==3.3.2
```

---


"""
Automated permission test script.

Run with:  python3 manage.py shell < test_permissions.py

It creates three users (admin / agent / customer1), assigns roles, creates
accounts + transactions, then exercises every permission path.
"""
import os, sys, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'fintech_api.settings')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
django.setup()

from django.contrib.auth.models import User
from rest_framework.test import APIRequestFactory
from rest_framework.request import Request as DRFRequest
from rest_framework_simplejwt.tokens import RefreshToken

from authentication.models import Role
from accounts.models import Account, Transaction
from accounts.permissions import (
    IsAccountOwner,
    IsVerifiedUser,
    IsActiveAccount,
    IsAccountOwnerOrAdmin,
    IsAdmin,
    IsAgent,
    IsCustomer,
    HasRole,
    IsOwnerOrReadOnly,
    IsOwnerReadOnlyOrAdmin,
    And,
    Or,
)

factory = APIRequestFactory()
passed = 0
failed = 0

def check(label, result, expected=True):
    global passed, failed
    status = 'PASS' if result == expected else 'FAIL'
    if status == 'FAIL':
        failed += 1
        print(f'  [{status}] {label}  (got {result}, expected {expected})')
    else:
        passed += 1

# ── Clean previous run ───────────────────────────────────────────────────────
Transaction.objects.filter(reference_number__startswith='TXN-TEST-').delete()
Account.objects.filter(account_number__startswith='CUST').delete()
User.objects.filter(username__startswith='permtest_').delete()

# ── Users ────────────────────────────────────────────────────────────────────
admin_user = User.objects.create_superuser(
    username='permtest_admin', email='admin@test.com', password='pass1234'
)
agent_user = User.objects.create_user(
    username='permtest_agent', email='agent@test.com', password='pass1234',
    is_staff=True,
)
customer1 = User.objects.create_user(
    username='permtest_cust1', email='c1@test.com', password='pass1234',
)
customer2 = User.objects.create_user(
    username='permtest_cust2', email='c2@test.com', password='pass1234',
)

Role.objects.get_or_create(user=admin_user, defaults={'role': Role.ADMIN})
Role.objects.get_or_create(user=agent_user, defaults={'role': Role.AGENT})
Role.objects.get_or_create(user=customer1, defaults={'role': Role.CUSTOMER})
Role.objects.get_or_create(user=customer2, defaults={'role': Role.CUSTOMER})

# ── Accounts ─────────────────────────────────────────────────────────────────
acct1 = Account.objects.create(user=customer1, account_number='CUST1-001', account_type='SAVINGS', balance=5000)
acct2 = Account.objects.create(user=customer2, account_number='CUST2-001', account_type='SAVINGS', balance=3000)
acct_frozen = Account.objects.create(user=customer1, account_number='CUST1-FRZ', account_type='CHECKING', balance=1000, is_frozen=True)

# ── Transactions ─────────────────────────────────────────────────────────────
txn1 = Transaction.objects.create(
    account=acct1, transaction_type='DEPOSIT', amount=500,
    reference_number='TXN-TEST-001', status='COMPLETED',
)
txn2 = Transaction.objects.create(
    account=acct2, transaction_type='WITHDRAWAL', amount=100,
    reference_number='TXN-TEST-002', status='COMPLETED',
)

# ── Helper: build an authenticated DRF Request ───────────────────────────────
def make_request(user, method='get', data=None):
    wsgi = getattr(factory, method)('/api/test/', data=data, format='json')
    r = DRFRequest(wsgi)
    r._user = user
    r.user = user
    r.auth = {'role': Role.get_role_for_user(user), 'email': user.email}
    return r

# ── Test CombinablePermission (AND / OR) ────────────────────────────────────
print('\n=== CombinablePermission (AND / OR) ===')
p_and = And(IsVerifiedUser(), IsActiveAccount())
p_or  = Or(IsAdmin(), IsAgent())

req_c1 = make_request(customer1)
check('AND(Verified,Active) — normal account',
      p_and.has_permission(req_c1, None))
check('AND(Verified,Active) — frozen account (object)',
      not p_and.has_object_permission(req_c1, None, acct_frozen))

check('OR(Admin,Agent) — admin passes',
      p_or.has_permission(make_request(admin_user), None))
check('OR(Admin,Agent) — agent passes',
      p_or.has_permission(make_request(agent_user), None))
check('OR(Admin,Agent) — customer denied',
      not p_or.has_permission(make_request(customer1), None))

# ── Test IsAccountOwner ──────────────────────────────────────────────────────
print('\n=== IsAccountOwner ===')
perm = IsAccountOwner()
check('owner → has_object_permission',
      perm.has_object_permission(make_request(customer1), None, acct1))
check('non-owner → denied',
      not perm.has_object_permission(make_request(customer2), None, acct1))
check('admin (not owner) → denied',
      not perm.has_object_permission(make_request(admin_user), None, acct1))

# ── Test IsVerifiedUser ─────────────────────────────────────────────────────
print('\n=== IsVerifiedUser ===')
perm = IsVerifiedUser()
check('user with email → pass',
      perm.has_permission(make_request(customer1), None))
check('superuser (has email) → pass',
      perm.has_permission(make_request(admin_user), None))

# ── Test IsActiveAccount ─────────────────────────────────────────────────────
print('\n=== IsActiveAccount ===')
perm = IsActiveAccount()
check('normal account → pass',
      perm.has_object_permission(make_request(customer1), None, acct1))
check('frozen account → denied',
      not perm.has_object_permission(make_request(customer1), None, acct_frozen))

# ── Test IsAccountOwnerOrAdmin ───────────────────────────────────────────────
print('\n=== IsAccountOwnerOrAdmin ===')
perm = IsAccountOwnerOrAdmin()
check('owner → pass',
      perm.has_object_permission(make_request(customer1), None, acct1))
check('admin → pass',
      perm.has_object_permission(make_request(admin_user), None, acct1))
check('non-owner → denied',
      not perm.has_object_permission(make_request(customer2), None, acct1))

# ── Test HasRole / IsAdmin / IsAgent / IsCustomer ────────────────────────────
print('\n=== HasRole (RBAC) ===')
check('IsAdmin → admin passes',
      IsAdmin().has_permission(make_request(admin_user), None))
check('IsAdmin → agent denied',
      not IsAdmin().has_permission(make_request(agent_user), None))
check('IsAdmin → customer denied',
      not IsAdmin().has_permission(make_request(customer1), None))

check('IsAgent → agent passes',
      IsAgent().has_permission(make_request(agent_user), None))
check('IsAgent → admin denied',
      not IsAgent().has_permission(make_request(admin_user), None))
check('IsAgent → customer denied',
      not IsAgent().has_permission(make_request(customer1), None))

check('IsCustomer → customer passes',
      IsCustomer().has_permission(make_request(customer1), None))
check('IsCustomer → admin denied',
      not IsCustomer().has_permission(make_request(admin_user), None))

# ── Test IsOwnerOrReadOnly ───────────────────────────────────────────────────
print('\n=== IsOwnerOrReadOnly ===')
perm = IsOwnerOrReadOnly()
check('GET (safe) → owner allowed',
      perm.has_object_permission(make_request(customer1, 'get'), None, txn1))
check('GET (safe) → non-owner allowed (read-only)',
      perm.has_object_permission(make_request(customer2, 'get'), None, txn1))
check('POST (mutating) → owner allowed',
      perm.has_object_permission(make_request(customer1, 'post'), None, txn1))
check('POST (mutating) → non-owner denied',
      not perm.has_object_permission(make_request(customer2, 'post'), None, txn1))
check('PUT (mutating) → admin allowed',
      perm.has_object_permission(make_request(admin_user, 'put'), None, txn1))

# ── Test IsOwnerReadOnlyOrAdmin ──────────────────────────────────────────────
print('\n=== IsOwnerReadOnlyOrAdmin ===')
perm = IsOwnerReadOnlyOrAdmin()
check('GET → owner passes',
      perm.has_object_permission(make_request(customer1, 'get'), None, acct1))
check('GET → non-owner denied',
      not perm.has_object_permission(make_request(customer2, 'get'), None, acct1))
check('DELETE → owner passes',
      perm.has_object_permission(make_request(customer1, 'delete'), None, acct1))
check('DELETE → admin passes',
      perm.has_object_permission(make_request(admin_user, 'delete'), None, acct1))
check('DELETE → non-owner denied',
      not perm.has_object_permission(make_request(customer2, 'delete'), None, acct1))

# ── Test django-guardian assign_perm integration ─────────────────────────────
print('\n=== django-guardian assign_perm ===')
from guardian.shortcuts import assign_perm, get_objects_for_user

assign_perm('view_transaction', customer1, txn2)
check('guardian: customer1 has view_transaction on txn2',
      customer1.has_perm('accounts.view_transaction', txn2))
check('guardian: customer2 does NOT have view_transaction on txn2',
      not customer2.has_perm('accounts.view_transaction', txn2))

# ── Summary ──────────────────────────────────────────────────────────────────
print(f'\n{"=" * 60}')
print(f'  TOTAL: {passed + failed}  |  PASSED: {passed}  |  FAILED: {failed}')
print(f'{"=" * 60}')
if failed:
    sys.exit(1)

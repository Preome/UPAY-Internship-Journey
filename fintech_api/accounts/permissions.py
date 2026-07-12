"""
Custom permission classes for the fintech API.

Built-in DRF permissions:
    - IsAuthenticated: Allow only authenticated users
    - IsAdminUser: Allow only admin users (is_staff=True)
    - IsAuthenticatedOrReadOnly: Authenticated for write, anyone for read

Custom permissions implement object-level checks and RBAC.
django-guardian provides per-object permission lookups.
"""
from rest_framework.permissions import BasePermission, SAFE_METHODS


# ---------------------------------------------------------------------------
# Combinable base class — lets you compose permissions with & and |
# ---------------------------------------------------------------------------

class CombinablePermission(BasePermission):
    """
    Base class for permissions that can be composed.

    DRF's metaclass already overloads & and | on *class objects*.
    For *instances*, use the And / Or helpers directly:

        permission_classes = [And(IsAdmin(), IsAgent())]
        permission_classes = [Or(IsAdmin(), IsAgent())]
    """


class And(CombinablePermission):
    """Both child permissions must pass."""

    def __init__(self, *perms):
        self.perms = perms

    def has_permission(self, request, view):
        return all(p.has_permission(request, view) for p in self.perms)

    def has_object_permission(self, request, view, obj):
        return all(p.has_object_permission(request, view, obj) for p in self.perms)

    def __repr__(self):
        return ' & '.join(repr(p) for p in self.perms)


class Or(CombinablePermission):
    """At least one child permission must pass."""

    def __init__(self, *perms):
        self.perms = perms

    def has_permission(self, request, view):
        return any(p.has_permission(request, view) for p in self.perms)

    def has_object_permission(self, request, view, obj):
        return any(p.has_object_permission(request, view, obj) for p in self.perms)

    def __repr__(self):
        return ' | '.join(repr(p) for p in self.perms)


# ---------------------------------------------------------------------------
# 1. IsAccountOwner — the requesting user owns the target Account
# ---------------------------------------------------------------------------

class IsAccountOwner(CombinablePermission):
    """Object-level: the user owns the account."""

    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated

    def has_object_permission(self, request, view, obj):
        if hasattr(obj, 'user'):
            return obj.user == request.user
        if hasattr(obj, 'account'):
            return obj.account.user == request.user
        return False

    def __repr__(self):
        return 'IsAccountOwner'


# ---------------------------------------------------------------------------
# 2. IsVerifiedUser — user has a non-empty, verified email
# ---------------------------------------------------------------------------

class IsVerifiedUser(CombinablePermission):
    """User must have a verified email address (non-empty)."""

    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and request.user.email
            and request.user.email.strip() != ''
        )

    def has_object_permission(self, request, view, obj):
        return self.has_permission(request, view)

    def __repr__(self):
        return 'IsVerifiedUser'


# ---------------------------------------------------------------------------
# 3. IsActiveAccount — target account is not frozen
# ---------------------------------------------------------------------------

class IsActiveAccount(CombinablePermission):
    """Object-level: the target account is not frozen."""

    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated

    def has_object_permission(self, request, view, obj):
        account = getattr(obj, 'account', obj)
        if hasattr(account, 'is_frozen'):
            return not account.is_frozen
        return True

    def __repr__(self):
        return 'IsActiveAccount'


# ---------------------------------------------------------------------------
# 4. IsAccountOwnerOrAdmin — combines IsAccountOwner OR IsAdminUser
# ---------------------------------------------------------------------------

class IsAccountOwnerOrAdmin(CombinablePermission):
    """Shortcut: user owns the object OR is staff."""

    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated

    def has_object_permission(self, request, view, obj):
        if request.user.is_staff or request.user.is_superuser:
            return True
        if hasattr(obj, 'user'):
            return obj.user == request.user
        if hasattr(obj, 'account'):
            return obj.account.user == request.user
        return False

    def __repr__(self):
        return 'IsAccountOwnerOrAdmin'


# ---------------------------------------------------------------------------
# 5. HasRole — checks the role claim embedded in the JWT
# ---------------------------------------------------------------------------

class HasRole(CombinablePermission):
    """
    Check the 'role' claim in the JWT payload.

    Accepted values (set in the token serializer):
        'admin'  – superuser
        'agent'  – is_staff but not superuser
        'customer' – regular user
    """

    def __init__(self, *allowed_roles):
        self.allowed_roles = set(allowed_roles)

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        role = getattr(request, 'auth', None)
        if role is None:
            return False
        token_role = role.get('role', '') if hasattr(role, 'get') else ''
        return token_role in self.allowed_roles

    def has_object_permission(self, request, view, obj):
        return self.has_permission(request, view)

    def __repr__(self):
        return f'HasRole({",".join(sorted(self.allowed_roles))})'


# Concrete role shortcuts built on HasRole
class IsAdmin(HasRole):
    def __init__(self):
        super().__init__('admin')

    def __repr__(self):
        return 'IsAdmin'


class IsAgent(HasRole):
    def __init__(self):
        super().__init__('agent')

    def __repr__(self):
        return 'IsAgent'


class IsCustomer(HasRole):
    def __init__(self):
        super().__init__('customer')

    def __repr__(self):
        return 'IsCustomer'


# ---------------------------------------------------------------------------
# 6. IsOwnerOrReadOnly — object-level row security for any model with
#    a 'user' FK or nested 'account.user' chain
# ---------------------------------------------------------------------------

class IsOwnerOrReadOnly(CombinablePermission):
    """
    Row-level security:
    - Safe methods (GET, HEAD, OPTIONS): any authenticated user
      (queryset filtering already scopes the data).
    - Mutating methods: the user must own the object.
    """

    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated

    def has_object_permission(self, request, view, obj):
        if request.method in SAFE_METHODS:
            return True
        return self._is_owner(request.user, obj)

    @staticmethod
    def _is_owner(user, obj):
        if user.is_staff or user.is_superuser:
            return True
        if hasattr(obj, 'user'):
            return obj.user == user
        if hasattr(obj, 'account') and hasattr(obj.account, 'user'):
            return obj.account.user == user
        return False

    def __repr__(self):
        return 'IsOwnerOrReadOnly'


# ---------------------------------------------------------------------------
# 7. IsOwnerReadOnlyOrAdmin — read: owner; write: owner OR admin
# ---------------------------------------------------------------------------

class IsOwnerReadOnlyOrAdmin(CombinablePermission):
    """
    Object-level:
    - GET / HEAD / OPTIONS: user must own the object
    - POST / PUT / PATCH / DELETE: user must own OR be admin
    """

    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated

    def has_object_permission(self, request, view, obj):
        is_owner = self._is_owner(request.user, obj)
        if request.method in SAFE_METHODS:
            return is_owner
        return is_owner or request.user.is_staff or request.user.is_superuser

    @staticmethod
    def _is_owner(user, obj):
        if hasattr(obj, 'user'):
            return obj.user == user
        if hasattr(obj, 'account') and hasattr(obj.account, 'user'):
            return obj.account.user == user
        return False

    def __repr__(self):
        return 'IsOwnerReadOnlyOrAdmin'

from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet
from rest_framework.generics import GenericAPIView
from rest_framework.mixins import ListModelMixin, CreateModelMixin
from rest_framework.permissions import IsAuthenticated, AllowAny, IsAdminUser, IsAuthenticatedOrReadOnly
from django.shortcuts import get_object_or_404

from .models import Account, Transaction
from .serializers import (
    AccountListSerializer,
    AccountDetailSerializer,
    TransactionSerializer,
    FreezeAccountSerializer,
    ReverseTransactionSerializer,
)
from .permissions import (
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
)


# ---------------------------------------------------------------------------
# Way 1: APIView — full manual control, permission_classes explicit
# ---------------------------------------------------------------------------

class AccountAPIView(APIView):
    """
    APIView implementation — compare raw DRF permission usage.

    Built-in permissions demonstrated:
        IsAuthenticated  → only logged-in users may access
    Custom permission  → IsAccountOwnerOrAdmin on retrieve
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        accounts = Account.objects.filter(user=request.user)
        serializer = AccountListSerializer(accounts, many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = AccountListSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(user=request.user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# ---------------------------------------------------------------------------
# Way 2: GenericAPIView + Mixins
# ---------------------------------------------------------------------------

class AccountGenericView(GenericAPIView, ListModelMixin, CreateModelMixin):
    """
    GenericAPIView — uses built-in IsAuthenticatedOrReadOnly:
        safe methods: anyone (including unauthenticated) can read
        mutating methods: only authenticated users
    """
    queryset = Account.objects.all()
    serializer_class = AccountListSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]

    def get_queryset(self):
        return self.queryset.filter(user=self.request.user)

    def get(self, request, *args, **kwargs):
        return self.list(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        return self.create(request, *args, **kwargs)


# ---------------------------------------------------------------------------
# Way 3: ModelViewSet — RBAC + object-level permissions
# ---------------------------------------------------------------------------

class AccountViewSet(ModelViewSet):
    """
    RBAC mapping:
        list / create  → customer, agent, admin
        retrieve / update / destroy → owner OR admin
        freeze          → admin OR agent
        statement       → owner OR admin
    """
    queryset = Account.objects.all()

    def get_permissions(self):
        if self.action in ('list', 'create'):
            return [IsAuthenticated()]
        if self.action == 'freeze':
            return [IsAdmin() | IsAgent()]
        if self.action in ('retrieve', 'statement'):
            return [IsAccountOwnerOrAdmin()]
        # update / partial_update / destroy
        return [IsAccountOwnerOrAdmin()]

    def get_queryset(self):
        user = self.request.user
        if user.is_staff or user.is_superuser:
            return Account.objects.all()
        return Account.objects.filter(user=user)

    def get_serializer_class(self):
        if self.action == 'list':
            return AccountListSerializer
        return AccountDetailSerializer

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @action(detail=True, methods=['post'])
    def freeze(self, request, pk=None):
        account = self.get_object()
        if account.is_frozen:
            return Response(
                {'error': 'Account is already frozen'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        account.is_frozen = True
        account.save()
        reason = request.data.get('reason', 'No reason provided')
        return Response({
            'status': 'frozen',
            'account_id': account.id,
            'account_number': account.account_number,
            'reason': reason,
        })

    @action(detail=True, methods=['get'])
    def statement(self, request, pk=None):
        account = self.get_object()
        self.check_object_permissions(request, account)
        transactions = account.transactions.all()[:50]
        serializer = TransactionSerializer(transactions, many=True)
        return Response({
            'account_id': account.id,
            'account_number': account.account_number,
            'account_type': account.account_type,
            'current_balance': account.balance,
            'is_frozen': account.is_frozen,
            'transactions': serializer.data,
        })


# ---------------------------------------------------------------------------
# TransactionViewSet — row-level security: users see only their transactions
# ---------------------------------------------------------------------------

class TransactionViewSet(ModelViewSet):
    """
    Row-level security:
        list / create    → owner's transactions only (get_queryset filters)
        retrieve / update / destroy → object-level IsOwnerOrReadOnly check
        reverse          → owner OR admin

    django-guardian: assign_perm / assign_perm used for per-object grants
    when an agent needs to view a customer's transaction.
    """
    serializer_class = TransactionSerializer
    queryset = Transaction.objects.all()

    def get_permissions(self):
        if self.action == 'reverse':
            return [IsOwnerOrReadOnly()]
        return [IsOwnerOrReadOnly()]

    def get_queryset(self):
        user = self.request.user
        if user.is_staff or user.is_superuser:
            return Transaction.objects.all()
        from guardian.shortcuts import assign_perm
        qs = Transaction.objects.filter(account__user=user)
        agent_perm_qs = Transaction.objects.none()
        if user.is_staff:
            agent_perm_qs = Transaction.objects.filter(
                account__user__role_profile__role='customer'
            )
        return (qs | agent_perm_qs).distinct()

    def get_object(self):
        obj = super().get_object()
        self.check_object_permissions(self.request, obj)
        return obj

    def perform_create(self, serializer):
        import uuid
        reference = f"TXN-{uuid.uuid4().hex[:10].upper()}"
        account = serializer.validated_data['account']
        transaction_type = serializer.validated_data['transaction_type']
        amount = serializer.validated_data['amount']

        if transaction_type == 'DEPOSIT':
            account.balance += amount
        elif transaction_type in ('WITHDRAWAL', 'TRANSFER'):
            if account.balance < amount:
                from rest_framework import serializers as drf_serializers
                raise drf_serializers.ValidationError("Insufficient balance")
            account.balance -= amount

        account.save()
        txn = serializer.save(reference_number=reference, status='COMPLETED')
        from guardian.shortcuts import assign_perm
        assign_perm('view_transaction', account.user, txn)
        assign_perm('change_transaction', account.user, txn)

    @action(detail=True, methods=['post'])
    def reverse(self, request, pk=None):
        transaction = self.get_object()
        if transaction.status == 'REVERSED':
            return Response(
                {'error': 'Transaction already reversed'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        reason = request.data.get('reason', '')
        if not reason:
            return Response(
                {'error': 'Reason is required for reversal'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        from django.utils import timezone
        from datetime import timedelta

        time_diff = timezone.now() - transaction.created_at
        if time_diff > timedelta(hours=24):
            return Response(
                {'error': 'Cannot reverse transactions older than 24 hours'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        reversal_type = 'WITHDRAWAL' if transaction.transaction_type == 'DEPOSIT' else 'DEPOSIT'
        reversal = Transaction.objects.create(
            account=transaction.account,
            transaction_type=reversal_type,
            amount=transaction.amount,
            description=f"Reversal of {transaction.reference_number}: {reason}",
            status='COMPLETED',
            reference_number=f"REV-{transaction.reference_number}",
        )
        transaction.status = 'REVERSED'
        transaction.save()

        account = transaction.account
        if transaction.transaction_type == 'DEPOSIT':
            account.balance -= transaction.amount
        else:
            account.balance += transaction.amount
        account.save()

        return Response({
            'status': 'reversed',
            'original_transaction': transaction.reference_number,
            'reversal_transaction': reversal.reference_number,
            'message': f"Transaction reversed successfully. Reason: {reason}",
        })

from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet
from rest_framework.generics import GenericAPIView
from rest_framework.mixins import ListModelMixin, CreateModelMixin
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404

from .models import Account, Transaction
from .serializers import (
    AccountListSerializer, 
    AccountDetailSerializer, 
    TransactionSerializer,
    FreezeAccountSerializer,
    ReverseTransactionSerializer
)




# Way 1: APIView (Most flexible, manual everything)
class AccountAPIView(APIView):
    """
    APIView implementation - Full control, but verbose
    Trade-offs: 
    + Maximum flexibility
    + Easy to implement custom behaviors
    - Lots of boilerplate code
    - Need to handle pagination, filtering manually
    - Best for: Complex business logic, non-CRUD operations
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


# Way 2: GenericAPIView + Mixins (Balance between control and convenience)
class AccountGenericView(GenericAPIView, ListModelMixin, CreateModelMixin):
    """
    GenericAPIView + Mixins implementation
    Trade-offs:
    + Built-in pagination, filtering, ordering
    + Less code than APIView
    + Still customizable via get_queryset, get_serializer_class
    - Mixin order matters
    - Still need multiple classes for full CRUD
    - Best for: Standard operations with some custom logic
    """
    queryset = Account.objects.all()
    serializer_class = AccountListSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return self.queryset.filter(user=self.request.user)
    
    def get(self, request, *args, **kwargs):
        return self.list(request, *args, **kwargs)
    
    def post(self, request, *args, **kwargs):
        return self.create(request, *args, **kwargs)


# Way 3: ModelViewSet (Most convenient)
class AccountViewSet(ModelViewSet):
    """
    ModelViewSet implementation - Full CRUD with minimal code
    """
    queryset = Account.objects.all()
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        # PART 4: Override to filter by logged-in user
        user = self.request.user
        return Account.objects.filter(user=user)
    
    def get_serializer_class(self):
        # PART 4: Different serializers for list vs detail
        if self.action == 'list':
            return AccountListSerializer
        return AccountDetailSerializer
    
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
    
    # PART 3: Custom actions
    @action(detail=True, methods=['post'])
    def freeze(self, request, pk=None):
        account = self.get_object()
        
        if account.is_frozen:
            return Response(
                {'error': 'Account is already frozen'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        account.is_frozen = True
        account.save()
        
        reason = request.data.get('reason', 'No reason provided')
        
        return Response({
            'status': 'frozen',
            'account_id': account.id,
            'account_number': account.account_number,
            'reason': reason
        })
    
    @action(detail=True, methods=['get'])
    def statement(self, request, pk=None):
        account = self.get_object()
        transactions = account.transactions.all()[:50]  # Last 50 transactions
        
        serializer = TransactionSerializer(transactions, many=True)
        
        return Response({
            'account_id': account.id,
            'account_number': account.account_number,
            'account_type': account.account_type,
            'current_balance': account.balance,
            'is_frozen': account.is_frozen,
            'transactions': serializer.data
        })


class TransactionViewSet(ModelViewSet):
    serializer_class = TransactionSerializer
    queryset = Transaction.objects.all()
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        # Filter transactions by logged-in user's accounts
        return Transaction.objects.filter(account__user=self.request.user)
    
    def perform_create(self, serializer):
        # Generate unique reference number
        import uuid
        reference = f"TXN-{uuid.uuid4().hex[:10].upper()}"
        
        # Update account balance based on transaction type
        account = serializer.validated_data['account']
        transaction_type = serializer.validated_data['transaction_type']
        amount = serializer.validated_data['amount']
        
        if transaction_type == 'DEPOSIT':
            account.balance += amount
        elif transaction_type == 'WITHDRAWAL':
            if account.balance < amount:
                from rest_framework import serializers as drf_serializers
                raise drf_serializers.ValidationError("Insufficient balance")
            account.balance -= amount
        elif transaction_type == 'TRANSFER':
            if account.balance < amount:
                from rest_framework import serializers as drf_serializers
                raise drf_serializers.ValidationError("Insufficient balance")
            account.balance -= amount
        
        account.save()
        serializer.save(reference_number=reference, status='COMPLETED')
    
    @action(detail=True, methods=['post'])
    def reverse(self, request, pk=None):
        transaction = self.get_object()
        
        if transaction.status == 'REVERSED':
            return Response(
                {'error': 'Transaction already reversed'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        reason = request.data.get('reason', '')
        if not reason:
            return Response(
                {'error': 'Reason is required for reversal'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check if enough time has passed (optional, e.g., within 24 hours)
        from django.utils import timezone
        from datetime import timedelta
        
        time_diff = timezone.now() - transaction.created_at
        if time_diff > timedelta(hours=24):
            return Response(
                {'error': 'Cannot reverse transactions older than 24 hours'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # reversal transaction
        reversal_transaction_type = 'WITHDRAWAL' if transaction.transaction_type == 'DEPOSIT' else 'DEPOSIT'
        
        reversal = Transaction.objects.create(
            account=transaction.account,
            transaction_type=reversal_transaction_type,
            amount=transaction.amount,
            description=f"Reversal of {transaction.reference_number}: {reason}",
            status='COMPLETED',
            reference_number=f"REV-{transaction.reference_number}"
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
            'message': f"Transaction reversed successfully. Reason: {reason}"
        })
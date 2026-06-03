from rest_framework import serializers
from .models import Account, Transaction

class AccountListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Account
        fields = ['id', 'account_number', 'account_type', 'balance', 'is_frozen']
        read_only_fields = ['balance']


class AccountDetailSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source='user.username', read_only=True)
    transaction_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Account
        fields = ['id', 'account_number', 'account_type', 'balance', 'is_frozen', 
                  'user_name', 'created_at', 'updated_at', 'transaction_count']
        read_only_fields = ['balance', 'created_at', 'updated_at']
    
    def get_transaction_count(self, obj):
        return obj.transactions.count()


class TransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Transaction
        fields = '__all__'
        read_only_fields = ['reference_number', 'status', 'created_at']


class FreezeAccountSerializer(serializers.Serializer):
    reason = serializers.CharField(required=False, allow_blank=True)


class ReverseTransactionSerializer(serializers.Serializer):
    reason = serializers.CharField(required=True, max_length=255)
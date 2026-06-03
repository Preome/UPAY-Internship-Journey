from django.contrib import admin
from .models import Account, Transaction

@admin.register(Account)
class AccountAdmin(admin.ModelAdmin):
    list_display = ['account_number', 'user', 'account_type', 'balance', 'is_frozen', 'created_at']
    list_filter = ['account_type', 'is_frozen', 'created_at']
    search_fields = ['account_number', 'user__username']
    readonly_fields = ['balance', 'created_at', 'updated_at']
    list_editable = ['is_frozen']

@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ['reference_number', 'account', 'transaction_type', 'amount', 'status', 'created_at']
    list_filter = ['transaction_type', 'status', 'created_at']
    search_fields = ['reference_number', 'account__account_number', 'description']
    readonly_fields = ['reference_number', 'created_at']
    list_editable = ['status']
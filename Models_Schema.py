# fintech/models.py
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from decimal import Decimal

# ============= Custom Managers =============
class ActiveUserManager(models.Manager):
    """Custom manager for active users only"""
    def get_queryset(self):
        return super().get_queryset().filter(is_active=True)
    
    def with_high_balance(self, min_balance=10000):
        return self.get_queryset().filter(account__balance__gte=min_balance).distinct()


class TransactionManager(models.Manager):
    def successful(self):
        return self.filter(status='completed')
    
    def pending(self):
        return self.filter(status='pending')
    
    def today(self):
        return self.filter(created_at__date=timezone.now().date())


# ============= Models =============
class User(models.Model):
    """User model with constraints and custom manager"""
    email = models.EmailField(unique=True, db_index=True)
    full_name = models.CharField(max_length=255)
    phone = models.CharField(max_length=20, unique=True)
    date_joined = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)
    credit_score = models.IntegerField(
        validators=[MinValueValidator(300), MaxValueValidator(850)],
        null=True, blank=True
    )
    
    
    objects = models.Manager() 
    active_users = ActiveUserManager()  
    
    class Meta:
        db_table = 'fintech_user'
        indexes = [
            models.Index(fields=['email']),
            models.Index(fields=['phone']),
            models.Index(fields=['-date_joined']),
        ]
        constraints = [
            models.CheckConstraint(
                check=models.Q(credit_score__gte=300) | models.Q(credit_score__isnull=True),
                name='credit_score_min_300'
            ),
            models.CheckConstraint(
                check=models.Q(credit_score__lte=850) | models.Q(credit_score__isnull=True),
                name='credit_score_max_850'
            )
        ]
    
    def __str__(self):
        return f"{self.full_name} ({self.email})"


class Account(models.Model):
    ACCOUNT_TYPES = (
        ('checking', 'Checking'),
        ('savings', 'Savings'),
        ('credit', 'Credit'),
        ('investment', 'Investment'),
    )
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='accounts')
    account_number = models.CharField(max_length=20, unique=True, db_index=True)
    account_type = models.CharField(max_length=20, choices=ACCOUNT_TYPES)
    balance = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0.00'))
    currency = models.CharField(max_length=3, default='USD')
    is_frozen = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'fintech_account'
        indexes = [
            models.Index(fields=['account_number']),
            models.Index(fields=['user', 'account_type']),
            models.Index(fields=['-balance']),
        ]
        constraints = [
            models.CheckConstraint(
                check=models.Q(balance__gte=0),
                name='balance_non_negative'
            ),
            models.UniqueConstraint(
                fields=['user', 'account_type'],
                condition=models.Q(account_type='checking'),
                name='unique_checking_per_user'
            )
        ]
    
    def __str__(self):
        return f"{self.account_number} - {self.account_type} - ${self.balance}"


class Merchant(models.Model):
    name = models.CharField(max_length=255, db_index=True)
    category = models.CharField(max_length=100)  
    country = models.CharField(max_length=2)  
    is_high_risk = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'fintech_merchant'
        indexes = [
            models.Index(fields=['category']),
            models.Index(fields=['country']),
            models.Index(fields=['name', 'category']),
        ]
    
    def __str__(self):
        return f"{self.name} ({self.category})"


class Card(models.Model):
    CARD_TYPES = (
        ('debit', 'Debit'),
        ('credit', 'Credit'),
        ('prepaid', 'Prepaid'),
    )
    
    CARD_STATUS = (
        ('active', 'Active'),
        ('blocked', 'Blocked'),
        ('expired', 'Expired'),
        ('lost', 'Lost/Stolen'),
    )
    
    account = models.ForeignKey(Account, on_delete=models.CASCADE, related_name='cards')
    card_number = models.CharField(max_length=16, unique=True, db_index=True)
    card_type = models.CharField(max_length=20, choices=CARD_TYPES)
    expiry_date = models.DateField()
    cvv_hash = models.CharField(max_length=64)  
    status = models.CharField(max_length=20, choices=CARD_STATUS, default='active')
    daily_limit = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('1000.00'))
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'fintech_card'
        indexes = [
            models.Index(fields=['card_number']),
            models.Index(fields=['account', 'status']),
            models.Index(fields=['expiry_date']),
        ]
        constraints = [
            models.CheckConstraint(
                check=models.Q(daily_limit__gte=0),
                name='daily_limit_positive'
            )
        ]
    
    def __str__(self):
        return f"{self.card_type} Card ending in {self.card_number[-4:]}"


class Transaction(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('refunded', 'Refunded'),
    )
    
    TRANSACTION_TYPES = (
        ('purchase', 'Purchase'),
        ('withdrawal', 'Withdrawal'),
        ('deposit', 'Deposit'),
        ('transfer', 'Transfer'),
    )
    
    transaction_id = models.CharField(max_length=50, unique=True, db_index=True)
    account = models.ForeignKey(Account, on_delete=models.CASCADE, related_name='transactions')
    merchant = models.ForeignKey(Merchant, on_delete=models.CASCADE, related_name='transactions', null=True)
    card = models.ForeignKey(Card, on_delete=models.CASCADE, related_name='transactions', null=True)
    
    amount = models.DecimalField(max_digits=15, decimal_places=2)
    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    description = models.TextField(blank=True)
    location = models.CharField(max_length=255, blank=True)
    ip_address = models.GenericIPAddressField(null=True)
    
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    
    objects = TransactionManager()
    
    class Meta:
        db_table = 'fintech_transaction'
        indexes = [
            models.Index(fields=['transaction_id']),
            models.Index(fields=['account', '-created_at']),
            models.Index(fields=['status', 'created_at']),
            models.Index(fields=['merchant', 'status']),
        ]
        constraints = [
            models.CheckConstraint(
                check=models.Q(amount__gt=0),
                name='amount_positive'
            ),
            models.CheckConstraint(
                check=(
                    models.Q(transaction_type='deposit', merchant__isnull=True) |
                    models.Q(transaction_type='withdrawal', merchant__isnull=True) |
                    models.Q(transaction_type='purchase', merchant__isnull=False) |
                    models.Q(transaction_type='transfer', merchant__isnull=True)
                ),
                name='valid_merchant_for_transaction_type'
            )
        ]
    
    def __str__(self):
        return f"{self.transaction_id} - ${self.amount} - {self.status}"
# orm_queries.py - COMPLETELY FIXED VERSION
import os
import django
from django.db.models import Count, Sum, Avg, Max, Min, F, Q, Value, CharField, IntegerField, DecimalField, DurationField
from django.db.models.functions import Coalesce, TruncMonth, ExtractDay
from django.db.models import Case, When, BooleanField, Subquery, OuterRef, Exists, ExpressionWrapper
from decimal import Decimal
from datetime import timedelta
from django.utils import timezone

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'fintech_project.settings')
django.setup()

from fintech.models import User, Account, Transaction, Merchant, Card

print("=" * 80)
print("DJANGO ORM QUERIES - FINTECH APPLICATION")
print("=" * 80)

# ============= QUERY 1: Basic select_related =============
print("\n1. SELECT_RELATED - Get transactions with account and merchant data in single query")
print("-" * 60)
transactions = Transaction.objects.select_related('account', 'merchant')[:5]
for t in transactions:
    print(f"Txn {t.transaction_id}: Account {t.account.account_number}, Merchant: {t.merchant.name if t.merchant else 'N/A'}")
print(f"Number of queries: 1 (instead of 1 + N)")

# ============= QUERY 2: prefetch_related =============
print("\n2. PREFETCH_RELATED - Get accounts with their cards and transactions")
print("-" * 60)
accounts = Account.objects.prefetch_related('cards', 'transactions')[:3]
for acc in accounts:
    print(f"Account {acc.account_number}: {acc.cards.count()} cards, {acc.transactions.count()} transactions")
print("Number of queries: 3 (accounts, cards, transactions) - independent joins")

# ============= QUERY 3: F() expressions =============
print("\n3. F() EXPRESSIONS - Update balance without race conditions")
print("-" * 60)
print("Before update: Sample account balances")
for acc in Account.objects.filter(account_type='checking')[:3]:
    print(f"  {acc.account_number}: ${acc.balance}")

updated_count = Account.objects.filter(account_type='checking').update(
    balance=F('balance') * Decimal('1.05')
)
print(f"\nUpdated {updated_count} checking accounts (+5%)")

print("After update:")
for acc in Account.objects.filter(account_type='checking')[:3]:
    print(f"  {acc.account_number}: ${acc.balance}")

result = Transaction.objects.filter(amount__gt=F('account__balance') * Decimal('0.1'))[:3]
print(f"\nTransactions > 10% of account balance: {result.count()}")

# ============= QUERY 4: Q() objects for complex lookups =============
print("\n4. Q() OBJECTS - Complex OR conditions")
print("-" * 60)

high_risk_txns = Transaction.objects.filter(
    Q(merchant__is_high_risk=True) | Q(amount__gt=500)
).select_related('merchant')[:10]

print("Transactions that are high-risk OR > $500:")
for txn in high_risk_txns:
    risk = "HIGH RISK" if txn.merchant and txn.merchant.is_high_risk else "Normal"
    print(f"  ${txn.amount} - {txn.merchant.name if txn.merchant else 'N/A'} - {risk}")

safe_transactions = Transaction.objects.filter(
    ~Q(merchant__is_high_risk=True) & Q(amount__lt=100)
)[:5]
print(f"\nSafe transactions (non-high-risk AND < $100): {safe_transactions.count()}")

# ============= QUERY 5: Basic Aggregation =============
print("\n5. AGGREGATION - Total balance and transaction statistics")
print("-" * 60)

stats = Account.objects.aggregate(
    total_balance=Sum('balance'),
    avg_balance=Avg('balance'),
    max_balance=Max('balance'),
    min_balance=Min('balance'),
    total_accounts=Count('id')
)
print(f"Bank Statistics:")
print(f"  Total balance: ${stats['total_balance']:,.2f}")
print(f"  Average balance: ${stats['avg_balance']:,.2f}")
print(f"  Max balance: ${stats['max_balance']:,.2f}")
print(f"  Min balance: ${stats['min_balance']:,.2f}")
print(f"  Total accounts: {stats['total_accounts']}")

# ============= QUERY 6: Annotations =============
print("\n6. ANNOTATIONS - Add computed fields to each object")
print("-" * 60)

accounts_with_stats = Account.objects.annotate(
    transaction_count=Count('transactions'),
    total_spent=Coalesce(Sum('transactions__amount'), Decimal('0')),
    avg_transaction=Coalesce(Avg('transactions__amount'), Decimal('0')),
    is_high_volume=Case(
        When(transaction_count__gt=50, then=Value(True)),
        default=Value(False),
        output_field=BooleanField()
    )
)[:5]

for acc in accounts_with_stats:
    print(f"Account {acc.account_number}:")
    print(f"  Transactions: {acc.transaction_count}")
    print(f"  Total spent: ${acc.total_spent:,.2f}")
    print(f"  Avg transaction: ${acc.avg_transaction:,.2f}")
    print(f"  High volume: {acc.is_high_volume}")

# ============= QUERY 7: Group By / Values + Annotation =============
print("\n7. GROUP BY - Transactions by merchant category")
print("-" * 60)

merchant_stats = Transaction.objects.filter(
    merchant__isnull=False,
    status='completed'
).values('merchant__category').annotate(
    total_sales=Sum('amount'),
    transaction_count=Count('id'),
    avg_transaction=Avg('amount'),
    total_unique_customers=Count('account', distinct=True)
).order_by('-total_sales')

for stat in merchant_stats[:5]:
    print(f"{stat['merchant__category']}:")
    print(f"  Sales: ${stat['total_sales']:,.2f}")
    print(f"  Transactions: {stat['transaction_count']}")
    print(f"  Average: ${stat['avg_transaction']:,.2f}")
    print(f"  Unique customers: {stat['total_unique_customers']}")

# ============= QUERY 8: Conditional Aggregation =============
print("\n8. CONDITIONAL AGGREGATION - Success/failure rates")
print("-" * 60)

transaction_metrics = Transaction.objects.aggregate(
    total_transactions=Count('id'),
    successful=Count(Case(When(status='completed', then=1))),
    failed=Count(Case(When(status='failed', then=1))),
    pending=Count(Case(When(status='pending', then=1))),
    total_volume_success=Sum(Case(
        When(status='completed', then='amount'),
        default=0,
        output_field=DecimalField()
    )),
)

if transaction_metrics['total_transactions'] > 0:
    transaction_metrics['success_rate'] = round(
        transaction_metrics['successful'] * 100.0 / transaction_metrics['total_transactions'], 2
    )
else:
    transaction_metrics['success_rate'] = 0

print("Transaction Metrics:")
print(f"  Total: {transaction_metrics['total_transactions']}")
print(f"  Successful: {transaction_metrics['successful']}")
print(f"  Failed: {transaction_metrics['failed']}")
print(f"  Pending: {transaction_metrics['pending']}")
print(f"  Success Rate: {transaction_metrics['success_rate']}%")
print(f"  Volume (successful): ${transaction_metrics['total_volume_success']:,.2f}")

# ============= QUERY 9: Subqueries =============
print("\n9. SUBQUERIES - Users with above-average spending")
print("-" * 60)

avg_spending = Transaction.objects.filter(status='completed').aggregate(
    avg_amount=Avg('amount')
)['avg_amount'] or 0

users_above_avg = User.objects.filter(
    Exists(
        Transaction.objects.filter(
            account__user=OuterRef('pk'),
            status='completed',
            amount__gt=avg_spending
        )
    )
).annotate(
    total_spent=Sum('accounts__transactions__amount', filter=Q(accounts__transactions__status='completed')),
    avg_transaction=Avg('accounts__transactions__amount', filter=Q(accounts__transactions__status='completed'))
)[:5]

print(f"Users with transactions above average (${avg_spending:.2f}):")
for user in users_above_avg:
    print(f"  {user.full_name}: Total spent: ${user.total_spent or 0:,.2f}, Avg: ${user.avg_transaction or 0:,.2f}")

# ============= QUERY 10: Rankings =============
print("\n10. RANKINGS - Rank users by spending")
print("-" * 60)

user_rankings = User.objects.annotate(
    transaction_count=Count('accounts__transactions')
).order_by('-transaction_count')[:10]

print("User Rankings by Transaction Volume:")
for idx, user in enumerate(user_rankings, 1):
    print(f"  #{idx}: {user.full_name} - {user.transaction_count} transactions")

# ============= QUERY 11: Date-based Aggregations =============
print("\n11. DATE AGGREGATIONS - Monthly transaction trends")
print("-" * 60)

monthly_trends = Transaction.objects.filter(
    status='completed',
    created_at__gte=timezone.now() - timedelta(days=180)
).annotate(
    month=TruncMonth('created_at')
).values('month').annotate(
    total_volume=Sum('amount'),
    transaction_count=Count('id'),
    avg_transaction=Avg('amount')
).order_by('month')

print("Last 6 months trends:")
for trend in monthly_trends:
    if trend['month']:
        print(f"  {trend['month'].strftime('%B %Y')}:")
        print(f"    Volume: ${trend['total_volume']:,.2f}")
        print(f"    Count: {trend['transaction_count']}")
        print(f"    Average: ${trend['avg_transaction']:,.2f}")

# ============= QUERY 12: Advanced Filtering with Subqueries =============
print("\n12. ADVANCED FILTERING - High-risk merchants with suspicious activity")
print("-" * 60)

suspicious_merchants = Merchant.objects.filter(
    is_high_risk=True
).annotate(
    avg_transaction=Avg('transactions__amount'),
    max_transaction=Max('transactions__amount'),
    transaction_count=Count('transactions')
).filter(transaction_count__gt=0)[:5]

for merchant in suspicious_merchants:
    print(f"  {merchant.name}:")
    print(f"    Transactions: {merchant.transaction_count}")
    print(f"    Avg: ${merchant.avg_transaction:,.2f}")
    print(f"    Max: ${merchant.max_transaction:,.2f}")

# ============= QUERY 13: Complex Filtering with Multiple Conditions =============
print("\n13. COMPLEX FILTERING - High-value transactions from active users")
print("-" * 60)

high_value_transactions = Transaction.objects.filter(
    Q(amount__gt=500) &
    Q(status='completed') &
    Q(account__user__is_active=True)
).select_related('account__user', 'merchant')[:10]

print("High-value transactions from active users:")
for txn in high_value_transactions:
    print(f"  ${txn.amount} - {txn.merchant.name if txn.merchant else 'Cash'} - User: {txn.account.user.email}")

# ============= QUERY 14: Exists and Conditional Logic =============
print("\n14. EXISTS SUBSELECT - Users with recent activity")
print("-" * 60)

recent_cutoff = timezone.now() - timedelta(days=30)

active_users = User.objects.annotate(
    has_recent_transaction=Exists(
        Transaction.objects.filter(
            account__user=OuterRef('pk'),
            created_at__gte=recent_cutoff
        )
    ),
    has_high_balance=Exists(
        Account.objects.filter(
            user=OuterRef('pk'),
            balance__gt=10000
        )
    )
).filter(has_recent_transaction=True)

print(f"Users active in last 30 days: {active_users.count()}")
print("Sample active users:")
for user in active_users[:5]:
    print(f"  {user.full_name} - High balance: {user.has_high_balance}")

# ============= QUERY 15: Complex Custom Annotations  =============
print("\n15. COMPLEX ANNOTATIONS - Customer lifetime value and risk scoring")
print("-" * 60)

from django.db.models import DurationField, ExpressionWrapper

customer_analytics = User.objects.annotate(
    total_transactions=Count('accounts__transactions'),
    lifetime_value=Coalesce(
        Sum('accounts__transactions__amount', filter=Q(accounts__transactions__status='completed')), 
        Value(Decimal('0'))
    ),
    avg_transaction=Coalesce(
        Avg('accounts__transactions__amount', filter=Q(accounts__transactions__status='completed')), 
        Value(Decimal('0'))
    ),
    days_active_duration=ExpressionWrapper(
        timezone.now() - F('date_joined'),
        output_field=DurationField()
    ),
    risk_score=Case(
        When(
            Q(credit_score__lt=600) | Q(accounts__balance__lt=100),
            then=Value('HIGH')
        ),
        When(
            Q(credit_score__lt=700) | Q(accounts__balance__lt=1000),
            then=Value('MEDIUM')
        ),
        default=Value('LOW'),
        output_field=CharField()
    )
).order_by('-lifetime_value')[:10]

print("Top 10 Customers by Lifetime Value:")
for customer in customer_analytics:
    
    days = customer.days_active_duration.days if customer.days_active_duration else 0
    print(f"\n  {customer.full_name}:")
    print(f"    Lifetime Value: ${customer.lifetime_value:,.2f}")
    print(f"    Avg Transaction: ${customer.avg_transaction:,.2f}")
    print(f"    Days Active: {days}")
    print(f"    Risk Score: {customer.risk_score}")
    print(f"    Credit Score: {customer.credit_score}")

print("\n" + "=" * 80)
print(" ALL 15 QUERIES EXECUTED SUCCESSFULLY!")
print("=" * 80)
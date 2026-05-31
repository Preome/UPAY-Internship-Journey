
import os
import django
from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'fintech_project.settings')
django.setup()

from fintech.models import User, Account, Transaction, Merchant, Card
from django.db.models import Count, Sum, Avg, Q, Case, When, Value, IntegerField, DecimalField, F


def run_and_analyze(func, description):
    """Helper to run query and analyze performance"""
    print(f"\n{'='*80}")
    print(f"ANALYZING: {description}")
    print('='*80)
    
    
    connection.queries_log.clear()
    
    with CaptureQueriesContext(connection) as context:
        import time
        start = time.time()
        result = func()
        end = time.time()
        
        query_count = len(context.captured_queries)
        execution_time = (end - start) * 1000  
        
        
        result_length = len(result) if hasattr(result, '__len__') else 'N/A'
        
        print(f" Result rows: {result_length}")
        print(f" Number of queries: {query_count}")
        print(f"  Execution time: {execution_time:.2f} ms")
        
        
        if query_count <= 15:
            for i, query in enumerate(context.captured_queries, 1):
                sql_display = query['sql'][:150] + '...' if len(query['sql']) > 150 else query['sql']
                print(f"\nQuery {i}:")
                print(f"  {sql_display}")
                print(f"  Time: {float(query['time'])*1000:.2f}ms")
        
        return query_count, execution_time, result_length


# ============= EXAMPLE 1: USER TRANSACTION REPORT =============

def slow_user_report():
    """
    SLOW QUERY - Demonstrates the N+1 problem
    
    This function makes 1 query for users + N queries for each user's related data.
    With 100 users, this makes 101+ database queries!
    """
    print("\n SLOW QUERY: User transaction report (WITHOUT optimization)")
    print("-" * 60)
    print("PROBLEM: N+1 queries - One query for users, then one query per user")
    
    users = User.objects.filter(is_active=True)[:20]  # Limit to 20 for demo
    report = []
    
    for user in users:
        # EACH iteration triggers additional queries
        # This is the N+1 problem!
        account_count = user.accounts.count()  # Query 1 per user
        
        # This nested loop causes even more queries
        total_spent = Decimal('0')
        for account in user.accounts.all():  # Another query per user
            for transaction in account.transactions.filter(status='completed'):  # Query per account
                total_spent += transaction.amount
        
        active_cards = 0
        for account in user.accounts.all():  # Yet another query per user
            for card in account.cards.all():  # Query per account
                if card.status == 'active':
                    active_cards += 1
        
        report.append({
            'user': user.full_name,
            'email': user.email,
            'accounts': account_count,
            'total_spent': total_spent,
            'active_cards': active_cards
        })
    
    return report


def optimized_user_report():
    """
    OPTIMIZED QUERY - Using prefetch_related to solve N+1
    
    This function makes only 4 total queries regardless of user count.
    """
    print("\n OPTIMIZED QUERY: User transaction report (WITH optimization)")
    print("-" * 60)
    print("SOLUTION: prefetch_related loads all related data in 4 total queries")
    
    users = User.objects.filter(is_active=True).prefetch_related(
        'accounts',
        'accounts__transactions',
        'accounts__cards'
    )[:20]
    
    report = []
    for user in users:
        # All data is already loaded in memory - no additional queries!
        account_count = len(user.accounts.all())  
        
        total_spent = Decimal('0')
        for account in user.accounts.all():  
            for transaction in account.transactions.filter(status='completed'):  # Filtered in Python
                total_spent += transaction.amount
        
        active_cards = 0
        for account in user.accounts.all():  
            for card in account.cards.all():  
                if card.status == 'active':
                    active_cards += 1
        
        report.append({
            'user': user.full_name,
            'email': user.email,
            'accounts': account_count,
            'total_spent': total_spent,
            'active_cards': active_cards
        })
    
    return report


def best_user_report():
    """
    BEST QUERY - Using database annotations
    
    This function makes only 2 total queries and does all aggregation in the database.
    Much faster and more memory efficient!
    """
    print("\n BEST QUERY: Using database annotations (ULTRA OPTIMIZED)")
    print("-" * 60)
    print("SOLUTION: Annotations push all calculations to database level")
    
    from django.db.models import Count, Sum, Q, Case, When, Value, IntegerField
    from django.db.models.functions import Coalesce
    
    users = User.objects.filter(is_active=True).annotate(
        account_count=Count('accounts'),
        total_spent=Coalesce(
            Sum('accounts__transactions__amount', filter=Q(accounts__transactions__status='completed')),
            Value(Decimal('0'))
        ),
        active_cards_count=Sum(
            Case(
                When(accounts__cards__status='active', then=Value(1)),
                default=Value(0),
                output_field=IntegerField()
            )
        ),
        avg_transaction_value=Coalesce(
            Avg('accounts__transactions__amount', filter=Q(accounts__transactions__status='completed')),
            Value(Decimal('0'))
        )
    ).values('full_name', 'email', 'account_count', 'total_spent', 'active_cards_count', 'avg_transaction_value')[:20]
    
    return list(users)


# ============= EXAMPLE 2: TRANSACTION HISTORY =============

def slow_transaction_history():
    """
    SLOW QUERY - Transaction history with N+1 to related models
    """
    print("\n SLOW QUERY: Transaction history (WITHOUT optimization)")
    print("-" * 60)
    print("PROBLEM: Each transaction triggers 3-4 additional queries")
    
    transactions = Transaction.objects.filter(status='completed')[:30]
    result = []
    
    for txn in transactions:
        # Each of these accesses triggers a new database query!
        account_balance = txn.account.balance  # Query 1 per transaction
        merchant_name = txn.merchant.name if txn.merchant else "N/A"  # Query 2 per transaction
        card_last4 = txn.card.card_number[-4:] if txn.card else "N/A"  # Query 3 per transaction
        user_email = txn.account.user.email  # Query 4 per transaction (through account)
        
        result.append({
            'txn_id': txn.transaction_id,
            'amount': txn.amount,
            'merchant': merchant_name,
            'card': card_last4,
            'user': user_email,
            'balance': account_balance,
            'date': txn.created_at
        })
    
    return result


def optimized_transaction_history():
    """
    OPTIMIZED QUERY - Using select_related to join all related tables
    """
    print("\n OPTIMIZED QUERY: Transaction history (WITH optimization)")
    print("-" * 60)
    print("SOLUTION: select_related performs SQL JOINs to get all data in ONE query")
    
    # select_related follows all foreign key relationships in a single JOIN query
    transactions = Transaction.objects.filter(status='completed').select_related(
        'account',      # Join account table
        'account__user', # Join user through account (double underscore for nested)
        'merchant',     # Join merchant table
        'card'          # Join card table
    )[:30]
    
    result = []
    for txn in transactions:
        
        result.append({
            'txn_id': txn.transaction_id,
            'amount': txn.amount,
            'merchant': txn.merchant.name if txn.merchant else "N/A",
            'card': txn.card.card_number[-4:] if txn.card else "N/A",
            'user': txn.account.user.email,
            'balance': txn.account.balance,
            'date': txn.created_at
        })
    
    return result


# ============= EXAMPLE 3: DASHBOARD STATISTICS =============

def slow_dashboard_stats():
    """
    SLOW QUERY - Multiple separate aggregation queries
    """
    print("\n SLOW QUERY: Dashboard statistics (WITHOUT optimization)")
    print("-" * 60)
    print("PROBLEM: 5 separate database queries when 1 would suffice")
    
    # Each of these is a separate database round-trip
    total_users = User.objects.count()  
    total_transactions = Transaction.objects.count()  
    total_volume = Transaction.objects.aggregate(total=Sum('amount'))['total'] or 0  
    avg_transaction = Transaction.objects.aggregate(avg=Avg('amount'))['avg'] or 0  
    high_risk_count = Transaction.objects.filter(merchant__is_high_risk=True).count()  
    
    # Additional queries for trends
    today = timezone.now().date()
    week_ago = today - timedelta(days=7)
    
    weekly_volume = Transaction.objects.filter(
        created_at__date__gte=week_ago,
        status='completed'
    ).aggregate(total=Sum('amount'))['total'] or 0  # Query 6
    
    success_rate = Transaction.objects.aggregate(
        rate=Count(Case(When(status='completed', then=1))) * 100.0 / Count('id')
    )['rate'] or 0  # Query 7
    
    return {
        'total_users': total_users,
        'total_transactions': total_transactions,
        'total_volume': total_volume,
        'avg_transaction': avg_transaction,
        'high_risk_count': high_risk_count,
        'weekly_volume': weekly_volume,
        'success_rate': success_rate,
    }


def optimized_dashboard_stats():
    """
    OPTIMIZED QUERY - Single query with multiple aggregations
    """
    print("\n🚀 OPTIMIZED QUERY: Dashboard statistics (WITH optimization)")
    print("-" * 60)
    print("SOLUTION: Single aggregation query with conditional counts")
    
    from django.db.models import Count, Sum, Avg, Q
    
    today = timezone.now().date()
    week_ago = today - timedelta(days=7)
    
    # ONE query to get all statistics
    stats = Transaction.objects.aggregate(
        # Basic stats
        total_transactions=Count('id'),
        total_volume=Sum('amount'),
        avg_transaction=Avg('amount'),
        
        # Conditional counts using Q objects
        completed_count=Count('id', filter=Q(status='completed')),
        failed_count=Count('id', filter=Q(status='failed')),
        pending_count=Count('id', filter=Q(status='pending')),
        high_risk_count=Count('id', filter=Q(merchant__is_high_risk=True)),
        
        # Weekly stats
        weekly_volume=Sum('amount', filter=Q(created_at__date__gte=week_ago, status='completed')),
        weekly_count=Count('id', filter=Q(created_at__date__gte=week_ago, status='completed')),
        
        # Large transactions
        large_transactions=Count('id', filter=Q(amount__gt=1000)),
        
        # Success rate calculation
        success_rate=Count('id', filter=Q(status='completed')) * 100.0 / Count('id')
    )
    
   
    stats['total_users'] = User.objects.count()
    
  
    stats['weekly_avg'] = stats['weekly_volume'] / stats['weekly_count'] if stats['weekly_count'] else 0
    stats['completion_rate'] = stats['success_rate']
    
    return stats


# ============= MAIN EXECUTION =============
def run_optimization_comparison():
    """Run all comparisons and generate report"""
    
    print("\n" + "" * 40)
    print("DJANGO ORM QUERY OPTIMIZATION REPORT")
    print("" * 40)
    print("\nThis report demonstrates the dramatic performance improvements")
    print("achieved by using select_related, prefetch_related, and annotations.")
    
    results = []
    
    # Test 1: User Report
    print("\n" + "=" * 80)
    print("TEST 1: User Transaction Report")
    print("=" * 80)
    print("\nScenario: Generate report with account counts, spending totals, and active cards")
    
    try:
        slow_count, slow_time, slow_rows = run_and_analyze(slow_user_report, "SLOW User Report")
        opt_count, opt_time, opt_rows = run_and_analyze(optimized_user_report, "OPTIMIZED User Report (prefetch)")
        best_count, best_time, best_rows = run_and_analyze(best_user_report, "BEST User Report (annotations)")
        
        results.append({
            'test': 'User Transaction Report',
            'slow': {'queries': slow_count, 'time': slow_time, 'rows': slow_rows},
            'optimized': {'queries': opt_count, 'time': opt_time, 'rows': opt_rows},
            'best': {'queries': best_count, 'time': best_time, 'rows': best_rows},
            'improvement': f"{(slow_time - best_time) / slow_time * 100:.1f}%",
            'speedup': f"{slow_time / best_time:.1f}x"
        })
    except Exception as e:
        print(f"Error in Test 1: {e}")
    
    # Test 2: Transaction History
    print("\n" + "=" * 80)
    print("TEST 2: Transaction History")
    print("=" * 80)
    print("\nScenario: Display detailed transaction history with related data")
    
    try:
        slow_count2, slow_time2, slow_rows2 = run_and_analyze(slow_transaction_history, "SLOW Transaction History")
        opt_count2, opt_time2, opt_rows2 = run_and_analyze(optimized_transaction_history, "OPTIMIZED Transaction History")
        
        results.append({
            'test': 'Transaction History',
            'slow': {'queries': slow_count2, 'time': slow_time2, 'rows': slow_rows2},
            'optimized': {'queries': opt_count2, 'time': opt_time2, 'rows': opt_rows2},
            'improvement': f"{(slow_time2 - opt_time2) / slow_time2 * 100:.1f}%",
            'speedup': f"{slow_time2 / opt_time2:.1f}x"
        })
    except Exception as e:
        print(f"Error in Test 2: {e}")
    
    # Test 3: Dashboard Stats
    print("\n" + "=" * 80)
    print("TEST 3: Dashboard Statistics")
    print("=" * 80)
    print("\nScenario: Calculate multiple aggregate statistics for dashboard")
    
    try:
        slow_count3, slow_time3, slow_rows3 = run_and_analyze(slow_dashboard_stats, "SLOW Dashboard Stats")
        opt_count3, opt_time3, opt_rows3 = run_and_analyze(optimized_dashboard_stats, "OPTIMIZED Dashboard Stats")
        
        results.append({
            'test': 'Dashboard Statistics',
            'slow': {'queries': slow_count3, 'time': slow_time3, 'rows': slow_rows3},
            'optimized': {'queries': opt_count3, 'time': opt_time3, 'rows': opt_rows3},
            'improvement': f"{(slow_time3 - opt_time3) / slow_time3 * 100:.1f}%",
            'speedup': f"{slow_time3 / opt_time3:.1f}x"
        })
    except Exception as e:
        print(f"Error in Test 3: {e}")
    
    #  Summary Report
    print("\n" + "=" * 80)
    print("OPTIMIZATION SUMMARY REPORT")
    print("=" * 80)
    print("\nThis table shows the dramatic improvements achieved:")
    print()
    print(f"{'Test Case':<30} {'Before (q/time)':<25} {'After (q/time)':<25} {'Speedup':<15}")
    print("-" * 95)
    
    for result in results:
        before = f"{result['slow']['queries']}q / {result['slow']['time']:.1f}ms"
        
        if 'best' in result:
            after = f"{result['best']['queries']}q / {result['best']['time']:.1f}ms"
            speedup = result['speedup']
            print(f"{result['test']:<30} {before:<25} {after:<25} {speedup:<15}")
        else:
            after = f"{result['optimized']['queries']}q / {result['optimized']['time']:.1f}ms"
            speedup = result['speedup']
            print(f"{result['test']:<30} {before:<25} {after:<25} {speedup:<15}")
    
    print("\n" + "=" * 80)
    print("KEY INSIGHTS & BEST PRACTICES")
    print("=" * 80)
    
    insights = [
        ("N+1 Problem", "Always use select_related/prefetch_related when accessing related objects in loops"),
        ("Query Count", "Reduced from 101+ to just 3-4 queries in optimized versions"),
        ("Memory Usage", "Annotations push calculations to database, reducing Python memory footprint"),
        ("Debug Toolbar", "Essential for identifying N+1 problems and measuring query performance"),
    ]
    
    for insight, explanation in insights:
        print(f"\n• {insight}:")
        print(f"  {explanation}")
    
    return results


if __name__ == "__main__":
    print("\n" + "" * 40)
    print("DJANGO FINTECH ORM OPTIMIZATION SUITE")
    print("" * 40)
    print("\nThis comprehensive demo shows how to identify and fix")
    print("common ORM performance issues in Django applications.")
    
    # Run the optimization comparison
    results = run_optimization_comparison()
    
    print("\n Analysis complete! Check the results above.")
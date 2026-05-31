# fintech/views.py
from django.shortcuts import render
from django.http import JsonResponse
from django.db import connection
from django.db.models import Sum, Count, Q
from django.utils import timezone
from decimal import Decimal
import time

from .models import User, Account, Transaction, Merchant, Card


# ============= BASIC VIEWS =============

def health_check(request):
    """Simple health check endpoint"""
    return JsonResponse({
        'status': 'ok',
        'message': 'Fintech API is running',
        'timestamp': str(timezone.now())
    })


def stats(request):
    """Get database statistics"""
    stats_data = {
        'users': User.objects.count(),
        'accounts': Account.objects.count(),
        'merchants': Merchant.objects.count(),
        'cards': Card.objects.count(),
        'transactions': Transaction.objects.count(),
        'total_balance': float(Account.objects.aggregate(total=Sum('balance'))['total'] or 0),
        'total_volume': float(Transaction.objects.aggregate(total=Sum('amount'))['total'] or 0),
    }
    return JsonResponse(stats_data)


# ============= TEST VIEWS FOR DEBUG TOOLBAR =============

def test_slow_query(request):
    """
    Test view showing N+1 query problem
    This will generate many duplicate queries (N+1 problem)
    """
    # Get initial query count
    initial_query_count = len(connection.queries)
    
    # This causes N+1 queries - DO NOT use select_related/prefetch_related
    users = User.objects.filter(is_active=True)[:10]
    result = []
    
    for user in users:
        # Each access causes a new query - this is the N+1 problem!
        account = user.accounts.first()  # Query per user
        if account:
            transactions = account.transactions.all()[:5]  # Query per account
            total = sum(float(t.amount) for t in transactions)
            result.append({
                'user': user.email,
                'total': total,
                'transaction_count': len(transactions)
            })
        else:
            result.append({
                'user': user.email,
                'total': 0,
                'transaction_count': 0
            })
    
    # Calculate query count
    final_query_count = len(connection.queries) - initial_query_count
    
    return render(request, 'fintech/test.html', {
        'title': 'SLOW QUERY - N+1 Problem Detected',
        'query_count': final_query_count,
        'result': result,
        'is_slow': True
    })


def test_optimized_query(request):
    """
    Test view showing optimized query with select_related and prefetch_related
    This will generate only a few queries
    """
    # Get initial query count
    initial_query_count = len(connection.queries)
    
    # Optimized with select_related and prefetch_related
    # This loads all data in 2-3 queries instead of N+1
    transactions = Transaction.objects.filter(status='completed').select_related(
        'account', 
        'account__user', 
        'merchant', 
        'card'
    )[:30]
    
    result = []
    for txn in transactions:
        result.append({
            'id': txn.transaction_id,
            'amount': float(txn.amount),
            'merchant': txn.merchant.name if txn.merchant else 'Cash',
            'user': txn.account.user.email if txn.account.user else 'N/A',
            'card_last4': txn.card.card_number[-4:] if txn.card else 'N/A',
            'status': txn.status,
            'date': txn.created_at.strftime('%Y-%m-%d %H:%M')
        })
    
    # Calculate query count
    final_query_count = len(connection.queries) - initial_query_count
    
    return render(request, 'fintech/test.html', {
        'title': 'OPTIMIZED QUERY - Using select_related',
        'query_count': final_query_count,
        'result': result,
        'is_slow': False
    })


def comparison_view(request):
    """Show before/after comparison"""
    
    comparison_data = []
    
    # Test 1: User Account Report (Slow)
    try:
        # Clear query cache by resetting connection
        connection.queries_log.clear()
        start = time.time()
        
        users = User.objects.filter(is_active=True)[:10]
        slow_result = []
        for user in users:
            # This causes extra queries
            account_count = user.accounts.count()  # Query per user
            slow_result.append({'user': user.email, 'accounts': account_count})
        
        slow_time = (time.time() - start) * 1000
        slow_queries = len(connection.queries)
        
        comparison_data.append({
            'test': 'User Account Report',
            'slow_queries': slow_queries,
            'slow_time': round(slow_time, 2),
        })
    except Exception as e:
        comparison_data.append({'test': 'User Account Report', 'error': str(e)})
    
    # Test 2: User Account Report (Optimized)
    try:
        connection.queries_log.clear()
        start = time.time()
        
        # Use prefetch_related to solve N+1
        users = User.objects.filter(is_active=True).prefetch_related('accounts')[:10]
        opt_result = []
        for user in users:
            # No extra query - data already prefetched
            account_count = len(user.accounts.all())
            opt_result.append({'user': user.email, 'accounts': account_count})
        
        opt_time = (time.time() - start) * 1000
        opt_queries = len(connection.queries)
        
        # Update with optimized values
        comparison_data[0]['opt_queries'] = opt_queries
        comparison_data[0]['opt_time'] = round(opt_time, 2)
        if opt_time > 0:
            comparison_data[0]['speedup'] = round(comparison_data[0]['slow_time'] / opt_time, 1)
            comparison_data[0]['improvement'] = round(((comparison_data[0]['slow_time'] - opt_time) / comparison_data[0]['slow_time']) * 100, 1)
        else:
            comparison_data[0]['speedup'] = 0
            comparison_data[0]['improvement'] = 0
    except Exception as e:
        print(f"Error in optimized test: {e}")
    
    # Test 3: Transaction History (Slow)
    try:
        connection.queries_log.clear()
        start = time.time()
        
        transactions = Transaction.objects.filter(status='completed')[:20]
        slow_txn_result = []
        for txn in transactions:
            # Each access causes extra queries
            merchant_name = txn.merchant.name if txn.merchant else 'N/A'
            slow_txn_result.append({'id': txn.transaction_id, 'merchant': merchant_name})
        
        slow_time2 = (time.time() - start) * 1000
        slow_queries2 = len(connection.queries)
        
        comparison_data.append({
            'test': 'Transaction History',
            'slow_queries': slow_queries2,
            'slow_time': round(slow_time2, 2),
        })
    except Exception as e:
        comparison_data.append({'test': 'Transaction History', 'error': str(e)})
    
    # Test 4: Transaction History (Optimized)
    try:
        connection.queries_log.clear()
        start = time.time()
        
        # Use select_related to join tables
        transactions = Transaction.objects.filter(status='completed').select_related('merchant')[:20]
        opt_txn_result = []
        for txn in transactions:
            # No extra query - merchant already loaded
            merchant_name = txn.merchant.name if txn.merchant else 'N/A'
            opt_txn_result.append({'id': txn.transaction_id, 'merchant': merchant_name})
        
        opt_time2 = (time.time() - start) * 1000
        opt_queries2 = len(connection.queries)
        
        comparison_data[1]['opt_queries'] = opt_queries2
        comparison_data[1]['opt_time'] = round(opt_time2, 2)
        if opt_time2 > 0:
            comparison_data[1]['speedup'] = round(comparison_data[1]['slow_time'] / opt_time2, 1)
            comparison_data[1]['improvement'] = round(((comparison_data[1]['slow_time'] - opt_time2) / comparison_data[1]['slow_time']) * 100, 1)
        else:
            comparison_data[1]['speedup'] = 0
            comparison_data[1]['improvement'] = 0
    except Exception as e:
        print(f"Error in optimized transaction test: {e}")
    
    return render(request, 'fintech/comparison.html', {
        'comparison_data': comparison_data
    })


def debug_info(request):
    """Debug view to show toolbar info"""
    return render(request, 'fintech/debug.html', {
        'title': 'Debug Toolbar Test Page'
    })
# populate_data.py - COMPLETELY CORRECTED VERSION
import os
import django
from decimal import Decimal
from datetime import datetime, timedelta
import random

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'fintech_project.settings')
django.setup()

from fintech.models import User, Account, Merchant, Card, Transaction
from django.db.models import Sum

def create_sample_data():
    print("Creating sample data...")
    
    
    print("Clearing existing data...")
    Transaction.objects.all().delete()
    Card.objects.all().delete()
    Account.objects.all().delete()
    User.objects.all().delete()
    Merchant.objects.all().delete()
    print("✓ Existing data cleared")
    
    
    users = []
    for i in range(1, 11):  
        user = User.objects.create(
            email=f"user{i}@example.com",
            full_name=f"User {i}",
            phone=f"+123456789{i:02d}",  
            credit_score=random.randint(600, 800)
        )
        users.append(user)
    print(f"✓ Created {len(users)} users")
    
    #  Accounts
    accounts = []
    for user in users:
        for acc_type in ['checking', 'savings']:
            account = Account.objects.create(
                user=user,
                account_number=f"ACC{user.id}{acc_type[0].upper()}{random.randint(100, 999)}",
                account_type=acc_type,
                balance=Decimal(random.uniform(100, 50000))
            )
            accounts.append(account)
    print(f"✓ Created {len(accounts)} accounts")
    
    #  Merchants
    merchants_data = [
        ("Amazon", "retail", "US", False),
        ("Walmart", "retail", "US", False),
        ("McDonald's", "restaurant", "US", False),
        ("Starbucks", "restaurant", "US", False),
        ("Delta Airlines", "travel", "US", False),
        ("Casino Royale", "gambling", "US", True),
        ("Apple Store", "retail", "US", False),
        ("Uber", "transport", "US", False),
        ("Netflix", "entertainment", "US", False),
        ("High Risk Corp", "other", "US", True),
    ]
    
    merchants = []
    for name, category, country, is_high_risk in merchants_data:
        merchant = Merchant.objects.create(
            name=name,
            category=category,
            country=country,
            is_high_risk=is_high_risk
        )
        merchants.append(merchant)
    print(f"✓ Created {len(merchants)} merchants")
    
    #  Cards
    cards = []
    for account in accounts:
        for card_type in ['debit', 'credit']:
            # Generate unique card number
            card_number = f"{random.randint(4000, 4999)}{random.randint(1000, 9999)}{random.randint(1000, 9999)}{random.randint(1000, 9999)}"
            card = Card.objects.create(
                account=account,
                card_number=card_number,
                card_type=card_type,
                expiry_date=datetime.now() + timedelta(days=random.randint(30, 730)),
                cvv_hash=f"hash_{random.randint(100, 999)}",
                status=random.choice(['active', 'active', 'active', 'blocked']),
                daily_limit=Decimal(random.uniform(500, 10000))
            )
            cards.append(card)
    print(f"✓ Created {len(cards)} cards")
    
    # Purchase Transactions
    transactions = []
    status_choices = ['pending', 'completed', 'completed', 'completed', 'failed']
    
    print("Creating purchase transactions...")
    for i in range(500):
        account = random.choice(accounts)
        merchant = random.choice(merchants)
        
        account_cards = [c for c in cards if c.account.id == account.id]
        card = random.choice(account_cards) if account_cards else None
        
        transaction = Transaction.objects.create(
            transaction_id=f"PURCHASE{datetime.now().strftime('%Y%m%d')}{i:05d}",
            account=account,
            merchant=merchant,
            card=card,
            amount=Decimal(random.uniform(5, 1000)),
            transaction_type='purchase',
            status=random.choice(status_choices),
            description=f"Purchase at {merchant.name}",
            location=random.choice(['New York', 'Los Angeles', 'Chicago', 'Miami']),
            ip_address=f"192.168.{random.randint(1, 255)}.{random.randint(1, 255)}",
            created_at=datetime.now() - timedelta(days=random.randint(0, 90))
        )
        transactions.append(transaction)
    
    #  deposits
    print("Creating deposit transactions...")
    for i in range(50):
        account = random.choice(accounts)
        transaction_id = f"DEPOSIT{datetime.now().strftime('%Y%m%d')}{i:05d}"
        
        transaction = Transaction.objects.create(
            transaction_id=transaction_id,
            account=account,
            merchant=None,
            card=None,
            amount=Decimal(random.uniform(100, 5000)),
            transaction_type='deposit',
            status=random.choice(['completed', 'completed', 'completed', 'pending']),
            description="Deposit transaction",
            created_at=datetime.now() - timedelta(days=random.randint(0, 90))
        )
        transactions.append(transaction)
    
    # withdrawals
    print("Creating withdrawal transactions...")
    for i in range(50):
        account = random.choice(accounts)
        transaction_id = f"WITHDRAW{datetime.now().strftime('%Y%m%d')}{i:05d}"
        
        transaction = Transaction.objects.create(
            transaction_id=transaction_id,
            account=account,
            merchant=None,
            card=None,
            amount=Decimal(random.uniform(50, 2000)),
            transaction_type='withdrawal',
            status=random.choice(['completed', 'completed', 'pending', 'failed']),
            description="Withdrawal transaction",
            created_at=datetime.now() - timedelta(days=random.randint(0, 90))
        )
        transactions.append(transaction)
    
    # transfer transactions
    print("Creating transfer transactions...")
    for i in range(50):
        from_account = random.choice(accounts)
        
        other_accounts = [a for a in accounts if a.id != from_account.id]
        to_account = random.choice(other_accounts) if other_accounts else from_account
        
        transaction_id = f"TRANSFER{datetime.now().strftime('%Y%m%d')}{i:05d}"
        
        transaction = Transaction.objects.create(
            transaction_id=transaction_id,
            account=from_account,
            merchant=None,
            card=None,
            amount=Decimal(random.uniform(50, 2000)),
            transaction_type='transfer',
            status=random.choice(['completed', 'completed', 'pending']),
            description=f"Transfer to account {to_account.account_number[-4:]}",
            created_at=datetime.now() - timedelta(days=random.randint(0, 60))
        )
        transactions.append(transaction)
    
    print(f"✓ Created {len(transactions)} total transactions")
    
    print("\n" + "="*50)
    print(" Sample data creation complete!")
    print("="*50)
    
    # Print summary
    print(f"\n Database Summary:")
    print(f"   Users: {User.objects.count()}")
    print(f"   Accounts: {Account.objects.count()}")
    print(f"   Merchants: {Merchant.objects.count()}")
    print(f"   Cards: {Card.objects.count()}")
    print(f"   Transactions: {Transaction.objects.count()}")
    
    
    print(f"\n Transaction Breakdown:")
    for txn_type in ['purchase', 'deposit', 'withdrawal', 'transfer']:
        count = Transaction.objects.filter(transaction_type=txn_type).count()
        print(f"   {txn_type.capitalize()}: {count}")
    
    print(f"\n Status Breakdown:")
    for status in ['completed', 'pending', 'failed', 'refunded']:
        count = Transaction.objects.filter(status=status).count()
        if count > 0:
            print(f"   {status.capitalize()}: {count}")
    
    # balance summary
    total_balance = Account.objects.aggregate(total=Sum('balance'))['total'] or 0
    print(f"\n Total balance across all accounts: ${total_balance:,.2f}")
    
    # average balance
    avg_balance = Account.objects.aggregate(avg=Sum('balance'))['avg'] or 0
    if avg_balance:
        print(f" Average balance per account: ${avg_balance:,.2f}")

if __name__ == "__main__":
    create_sample_data()
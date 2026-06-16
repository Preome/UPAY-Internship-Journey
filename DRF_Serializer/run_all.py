import os
import sys
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "drf_serializer.settings")
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

os.environ["DJANGO_ALLOW_ASYNC_UNSAFE"] = "true"
django.setup()

from decimal import Decimal
from django.contrib.auth.models import User
from drf_serializer.models import Account, Transaction
from drf_serializer.serializers.basic_serializer import BasicSerializer
from drf_serializer.serializers.user_serializer import UserSerializer
from drf_serializer.serializers.account_serializers import (
    AccountSerializer,
    AccountDetailSerializer,
    AccountBulkSerializer,
)
from drf_serializer.serializers.transaction_serializers import (
    TransactionSerializer,
    NestedTransactionSerializer,
    TransactionCreateSerializer,
)
from drf_serializer.serializers.user_detail_serializer import UserDetailSerializer


def run_migrations():
    from django.core.management import call_command
    print("=" * 60)
    print("STEP 1: Running migrations...")
    call_command("makemigrations", "drf_serializer", verbosity=0)
    call_command("migrate", verbosity=0)
    print("Migrations complete.\n")


def run_tests():
    import pytest
    print("=" * 60)
    print("STEP 2: Running all tests...\n")
    test_dir = os.path.join(BASE_DIR, "drf_serializer", "tests")
    exit_code = pytest.main(
        [test_dir, "-v", "--tb=short", "-W", "ignore::DeprecationWarning"]
    )
    print(f"\nTests exit code: {exit_code}\n")
    return exit_code


def demonstrate():
    print("=" * 60)
    print("STEP 3: Serializer demonstrations\n")

    print("-" * 40)
    print("1. BasicSerializer (plain Serializer)")
    data = {"title": " Monthly Dues ", "amount": 50.00, "currency": "USD"}
    bs = BasicSerializer(data=data)
    assert bs.is_valid(), bs.errors
    print(f"   Validated: {bs.validated_data}")
    print(f"   Created:   {bs.save()}\n")

    print("-" * 40)
    print("2. UserSerializer (ModelSerializer)")
    user = User.objects.create_user(
        username="demouser", email="demo@example.com",
        first_name="Demo", last_name="User", password="test1234",
    )
    us = UserSerializer(user)
    print(f"   Output: {us.data}\n")

    print("-" * 40)
    print("3. AccountSerializer (ModelSerializer)")
    account = Account.objects.create(
        user=user, account_number="DEMO-001", account_type="SAVINGS",
        balance=Decimal("1250.00"), card_number="4111111111112468",
    )
    acct_s = AccountSerializer(account)
    print(f"   Output: {acct_s.data}\n")

    print("-" * 40)
    print("4. AccountDetailSerializer (with SerializerMethodField)")
    Transaction.objects.create(
        account=account, amount=Decimal("200.00"),
        transaction_type="DEPOSIT", description="Salary",
    )
    Transaction.objects.create(
        account=account, amount=Decimal("50.00"),
        transaction_type="WITHDRAWAL", description="Coffee",
    )
    ad = AccountDetailSerializer(account)
    print(f"   transaction_count: {ad.data['transaction_count']}")
    print(f"   last_transaction_amount: {ad.data['last_transaction_amount']}")
    print(f"   account_summary: {ad.data['account_summary']}")
    print(f"   meta: {ad.data['meta']}\n")

    print("-" * 40)
    print("5. UserDetailSerializer (to_representation override)")
    ud = UserDetailSerializer(user)
    print(f"   account_count: {ud.data['account_count']}")
    print(f"   total_balance: {ud.data['total_balance']}")
    print(f"   profile: {ud.data['profile']}")
    print(f"   role_label: {ud.data['role_label']}\n")

    print("-" * 40)
    print("6. TransactionSerializer (ModelSerializer)")
    txn = Transaction.objects.first()
    ts = TransactionSerializer(txn)
    print(f"   Output: {ts.data}\n")

    print("-" * 40)
    print("7. NestedTransactionSerializer (nested writable)")
    nested_data = {
        "amount": 999.99, "transaction_type": "TRANSFER",
        "description": "Nested demo",
        "account": {
            "account_number": "DEMO-NEST", "account_type": "CHECKING",
            "card_number": "5111111111118888", "is_active": True,
            "user": {
                "username": "nesteddemo", "email": "nested@demo.com",
                "first_name": "Nest", "last_name": "Demo",
                "password": "pass1234",
            },
        },
    }
    nt = NestedTransactionSerializer(data=nested_data)
    assert nt.is_valid(), nt.errors
    nested_txn = nt.save()
    print(f"   Created Transaction #{nested_txn.id}")
    print(f"   Account: {nested_txn.account.account_number}")
    print(f"   User: {nested_txn.account.user.username}")
    nt_read = NestedTransactionSerializer(nested_txn)
    print(f"   Serialized account: {nt_read.data['account']['account_number']}")
    print(f"   Card display: {nt_read.data['account']['card_display']}\n")

    print("-" * 40)
    print("8. AccountBulkSerializer (ListSerializer / bulk create)")
    bulk_data = [
        {
            "user": user.id, "account_number": f"BULK-{i:03d}",
            "account_type": "SAVINGS",
            "card_number": f"411111111111{i:04d}",
            "balance": Decimal(f"{i}00.00"),
        }
        for i in range(1, 4)
    ]
    bulk_s = AccountBulkSerializer(data=bulk_data, many=True)
    assert bulk_s.is_valid(), bulk_s.errors
    accounts = bulk_s.save()
    print(f"   Created {len(accounts)} accounts via bulk_create\n")

    print("-" * 40)
    print("9. TransactionCreateSerializer (flat Serializer)")
    flat_data = {
        "account_id": account.id, "amount": 75.00,
        "transaction_type": "PAYMENT",
    }
    tc = TransactionCreateSerializer(data=flat_data)
    assert tc.is_valid(), tc.errors
    flat_txn = tc.save()
    print(f"   Created Transaction #{flat_txn.id}\n")

    print("=" * 60)
    print("All serializer demonstrations completed successfully!")
    print("=" * 60)


if __name__ == "__main__":
    run_migrations()
    exit_code = run_tests()
    if exit_code == 0 or exit_code is True:
        demonstrate()
    else:
        print("Tests failed \u2014 skipping demonstrations.")
        sys.exit(1)

import pytest
from decimal import Decimal
from django.contrib.auth.models import User

from drf_serializer.models import Account, Transaction
from drf_serializer.serializers.basic_serializer import BasicSerializer
from drf_serializer.serializers.user_serializer import UserSerializer
from drf_serializer.serializers.account_serializers import (
    AccountSerializer,
    AccountBulkSerializer,
    AccountDetailSerializer,
)
from drf_serializer.serializers.transaction_serializers import (
    TransactionSerializer,
    NestedTransactionSerializer,
    TransactionCreateSerializer,
)
from drf_serializer.serializers.user_detail_serializer import (
    UserDetailSerializer,
)


@pytest.mark.django_db
class TestBasicSerializer:
    def test_valid_data(self):
        data = {"title": " Payment  ", "amount": 50.00, "currency": "USD"}
        serializer = BasicSerializer(data=data)
        assert serializer.is_valid()
        assert serializer.validated_data["title"] == "Payment"
        assert serializer.validated_data["amount"] == Decimal("50.00")

    def test_blank_title(self):
        data = {"title": "  ", "amount": 50.00, "currency": "USD"}
        serializer = BasicSerializer(data=data)
        assert not serializer.is_valid()
        assert "title" in serializer.errors

    def test_short_title(self):
        data = {"title": "ab", "amount": 50.00, "currency": "USD"}
        serializer = BasicSerializer(data=data)
        assert not serializer.is_valid()

    def test_negative_amount(self):
        data = {"title": "Test", "amount": -10.00, "currency": "USD"}
        serializer = BasicSerializer(data=data)
        assert not serializer.is_valid()

    def test_large_bdt(self):
        data = {"title": "Large", "amount": 2_000_000, "currency": "BDT"}
        serializer = BasicSerializer(data=data)
        assert not serializer.is_valid()


@pytest.mark.django_db
class TestUserSerializer:
    def test_serialize_user(self):
        user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            first_name="Test",
            last_name="User",
        )
        serializer = UserSerializer(user)
        assert serializer.data["username"] == "testuser"
        assert serializer.data["full_name"] == "Test User"
        assert "password" not in serializer.data

    def test_deserialize_valid(self):
        data = {
            "username": "newuser",
            "email": "new@example.com",
            "first_name": "New",
            "last_name": "User",
        }
        serializer = UserSerializer(data=data)
        assert serializer.is_valid()


@pytest.mark.django_db
class TestAccountSerializer:
    def test_serialize_account(self):
        user = User.objects.create_user(username="accuser")
        account = Account.objects.create(
            user=user,
            account_number="ACC-001",
            account_type="SAVINGS",
            balance=Decimal("500.00"),
            card_number="4111111111111234",
        )
        serializer = AccountSerializer(account)
        assert serializer.data["account_number"] == "ACC-001"
        assert "balance_bdt" in serializer.data
        assert serializer.data["card_display"] == "**** **** **** 1234"

    def test_validate_account_number(self):
        data = {
            "account_number": "AB",
            "account_type": "SAVINGS",
            "balance": 100,
            "card_number": "4111111111111111",
        }
        serializer = AccountSerializer(data=data)
        assert not serializer.is_valid()
        assert "account_number" in serializer.errors


@pytest.mark.django_db
class TestAccountDetailSerializer:
    def test_method_fields(self):
        user = User.objects.create_user(username="detailuser")
        account = Account.objects.create(
            user=user,
            account_number="ACC-DTL",
            balance=Decimal("1000.00"),
            card_number="4111111111115678",
        )
        Transaction.objects.create(
            account=account,
            amount=Decimal("200.00"),
            transaction_type="DEPOSIT",
        )
        serializer = AccountDetailSerializer(account)
        assert serializer.data["transaction_count"] == 1
        assert serializer.data["last_transaction_amount"] == 200.0
        assert "meta" in serializer.data
        assert serializer.data["meta"]["type"] == "account_detail"


@pytest.mark.django_db
class TestTransactionSerializer:
    def test_serialize_transaction(self):
        user = User.objects.create_user(username="txnuser")
        account = Account.objects.create(
            user=user,
            account_number="TXN-ACC",
            balance=Decimal("1000.00"),
            card_number="4111111111111111",
        )
        txn = Transaction.objects.create(
            account=account,
            amount=Decimal("250.00"),
            transaction_type="WITHDRAWAL",
            description="ATM withdrawal",
        )
        serializer = TransactionSerializer(txn)
        assert serializer.data["transaction_type"] == "WITHDRAWAL"
        assert serializer.data["description"] == "ATM withdrawal"
        assert "amount_taka" in serializer.data

    def test_validate_negative_amount(self):
        data = {
            "account": 1,
            "amount": -50,
            "transaction_type": "DEPOSIT",
        }
        serializer = TransactionSerializer(data=data)
        assert not serializer.is_valid()


@pytest.mark.django_db
class TestNestedTransactionSerializer:
    def test_create_nested_transaction(self):
        data = {
            "amount": 500.00,
            "transaction_type": "DEPOSIT",
            "description": "Nested create",
            "account": {
                "account_number": "NEST-001",
                "account_type": "CHECKING",
                "card_number": "4111111111119999",
                "is_active": True,
                "user": {
                    "username": "nesteduser",
                    "email": "nested@example.com",
                    "first_name": "Nest",
                    "last_name": "Ed",
                    "password": "testpass123",
                },
            },
        }
        serializer = NestedTransactionSerializer(data=data)
        assert serializer.is_valid(), serializer.errors
        txn = serializer.save()
        assert txn.id is not None
        assert txn.account.account_number == "NEST-001"
        assert txn.account.user.username == "nesteduser"
        assert txn.amount == Decimal("500.00")

    def test_create_missing_nested_fields(self):
        data = {
            "amount": 100.00,
            "transaction_type": "DEPOSIT",
        }
        serializer = NestedTransactionSerializer(data=data)
        assert not serializer.is_valid()
        assert "account" in serializer.errors


@pytest.mark.django_db
class TestTransactionCreateSerializer:
    def test_create_transaction(self):
        user = User.objects.create_user(username="createuser")
        account = Account.objects.create(
            user=user,
            account_number="CRT-ACC",
            balance=Decimal("500.00"),
            card_number="4111111111111111",
        )
        data = {
            "account_id": account.id,
            "amount": 150.00,
            "transaction_type": "DEPOSIT",
        }
        serializer = TransactionCreateSerializer(data=data)
        assert serializer.is_valid(), serializer.errors
        txn = serializer.save()
        assert txn.amount == Decimal("150.00")

    def test_invalid_account_id(self):
        data = {
            "account_id": 99999,
            "amount": 150.00,
            "transaction_type": "DEPOSIT",
        }
        serializer = TransactionCreateSerializer(data=data)
        assert not serializer.is_valid()
        assert "account_id" in serializer.errors


@pytest.mark.django_db
class TestUserDetailSerializer:
    def test_serialize_with_computed_fields(self):
        user = User.objects.create_user(
            username="detailuser",
            email="detail@example.com",
            first_name="Detail",
            last_name="User",
        )
        account = Account.objects.create(
            user=user,
            account_number="DTL-ACC",
            balance=Decimal("750.00"),
            card_number="4111111111111111",
        )
        Transaction.objects.create(
            account=account,
            amount=Decimal("100.00"),
            transaction_type="DEPOSIT",
        )
        serializer = UserDetailSerializer(user)
        assert serializer.data["account_count"] == 1
        assert serializer.data["total_balance"] == 750.0
        assert "profile" in serializer.data
        assert "Administrator" != serializer.data["role_label"]

    def test_to_internal_value_lowercases_username(self):
        user = User.objects.create_user(username="origuser")
        serializer = UserDetailSerializer(user, data={"username": "  NEWUSER  "})
        assert serializer.is_valid()
        assert serializer.validated_data["username"] == "newuser"


@pytest.mark.django_db
class TestAccountBulkSerializer:
    def test_bulk_create(self):
        user = User.objects.create_user(username="bulkuser")
        data = [
            {
                "user": user.id,
                "account_number": "BLK-001",
                "account_type": "SAVINGS",
                "card_number": "4111111111111111",
                "balance": 100,
            },
            {
                "user": user.id,
                "account_number": "BLK-002",
                "account_type": "CHECKING",
                "card_number": "4111111111111112",
                "balance": 200,
            },
        ]
        serializer = AccountBulkSerializer(data=data, many=True)
        assert serializer.is_valid(), serializer.errors
        accounts = serializer.save()
        assert len(accounts) == 2

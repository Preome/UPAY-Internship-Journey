# DRF Serializer Module

A comprehensive Django REST Framework serializer module covering all serializer types, custom fields, nested writable serializers, and best practices.



## Deliverable File Mapping

### 1. Full Serializer Module — 8+ Serializers

| Serializer Type | File | Description |
|---|---|---|
| Plain Serializer | [`DRF_Serializer/drf_serializer/serializers/basic_serializer.py`](../DRF_Serializer/drf_serializer/serializers/basic_serializer.py) | `BasicSerializer` — field-level + object-level validation |
| ModelSerializer | [`DRF_Serializer/drf_serializer/serializers/user_serializer.py`](../DRF_Serializer/drf_serializer/serializers/user_serializer.py) | `UserSerializer` — auto-generated fields from User model |
| ModelSerializer + MethodField | [`DRF_Serializer/drf_serializer/serializers/account_serializers.py`](../DRF_Serializer/drf_serializer/serializers/account_serializers.py) | `AccountSerializer`, `AccountDetailSerializer` (with computed fields) |
| ListSerializer | [`DRF_Serializer/drf_serializer/serializers/account_serializers.py`](../DRF_Serializer/drf_serializer/serializers/account_serializers.py) | `AccountListSerializer`, `AccountBulkSerializer` — bulk create/update |
| ModelSerializer (Transaction) | [`DRF_Serializer/drf_serializer/serializers/transaction_serializers.py`](../DRF_Serializer/drf_serializer/serializers/transaction_serializers.py) | `TransactionSerializer` |
| Nested Writable | [`DRF_Serializer/drf_serializer/serializers/transaction_serializers.py`](../DRF_Serializer/drf_serializer/serializers/transaction_serializers.py) | `NestedTransactionSerializer` — creates Transaction+Account+User in one call |
| Flat Serializer | [`DRF_Serializer/drf_serializer/serializers/transaction_serializers.py`](../DRF_Serializer/drf_serializer/serializers/transaction_serializers.py) | `TransactionCreateSerializer` — lightweight, no model coupling |
| ModelSerializer + Overrides | [`DRF_Serializer/drf_serializer/serializers/user_detail_serializer.py`](../DRF_Serializer/drf_serializer/serializers/user_detail_serializer.py) | `UserDetailSerializer` — `to_representation`, `to_internal_value` overrides |

### 2. Custom Field Classes — MoneyField + MaskedCardField

| File | Description |
|---|---|
| [`DRF_Serializer/drf_serializer/fields.py`](../DRF_Serializer/drf_serializer/fields.py) | `MoneyField` — stores USD, displays BDT (×120 conversion); `MaskedCardField` — shows only last 4 digits |
| [`DRF_Serializer/drf_serializer/tests/test_fields.py`](../DRF_Serializer/drf_serializer/tests/test_fields.py) | 11 tests covering both fields (conversion, masking, validation, edge cases) |

### 3. Nested Write Serializer — Create Transaction + Account in One API Call

| File | Description |
|---|---|
| [`DRF_Serializer/drf_serializer/serializers/transaction_serializers.py`](../DRF_Serializer/drf_serializer/serializers/transaction_serializers.py) | `NestedTransactionSerializer` + `AccountNestedSerializer` + `UserNestedSerializer` — fully writable 3-level nesting with password hashing |
| [`DRF_Serializer/drf_serializer/tests/test_serializers.py`](../DRF_Serializer/drf_serializer/tests/test_serializers.py) | `TestNestedTransactionSerializer` — validates create and missing-field scenarios |

### 4. Written Comparison — Choosing the Right Serializer Type

| File | Description |
|---|---|
| [`DRF_Serializer/comparison.md`](../DRF_Serializer/comparison.md) | 1-page guide: when to use Serializer vs ModelSerializer vs nested vs flat, decision flowchart, quick-reference table |

---

## DRF Serializer Concepts

For a browsable index of all DRF serializer concepts with direct file references, run:

```bash
python UPAY-Internship-Journey/DRF_Serializer_concepts.py
```

Or open [`DRF_Serializer_concepts.py`](./DRF_Serializer_concepts.py) to see the full mapping.

## Running the Project

```bash
cd DRF_Serializer
python run_all.py
```

This runs migrations, all 37 tests, and demonstrates every serializer type live.

## Broken Serializer Patterns

See [`DRF_Serializer/broken_serializer_patterns.txt`](../DRF_Serializer/broken_serializer_patterns.txt) for 5 common bugs and their fixes.

# Choosing the Right DRF Serializer Type

## 1. Serializer (Plain)

| Aspect | Details |
|---|---|
| **When to use** | Non-model data, API wrappers, computed payloads, form-like validation |
| **Pros** | Full control over fields, no DB coupling, lightweight |
| **Cons** | Must manually implement `create()`/`update()`, no auto-field generation |
| **Example** | `BasicSerializer` — validates title/amount/currency without a model |

## 2. ModelSerializer

| Aspect | Details |
|---|---|
| **When to use** | CRUD for a single model, 80% of API endpoints |
| **Pros** | Auto-generates fields from model, built-in `create()`/`update()`, less boilerplate |
| **Cons** | Can expose fields unintentionally, needs `read_only_fields` or `extra_kwargs` for control |
| **Example** | `UserSerializer`, `AccountSerializer`, `TransactionSerializer` |

## 3. ListSerializer

| Aspect | Details |
|---|---|
| **When to use** | Bulk create/update (POST/PUT arrays), batch operations |
| **Pros** | Single API call for multiple objects, `bulk_create` support |
| **Cons** | Complex error handling per-item, no partial failure without custom logic |
| **Example** | `AccountListSerializer` with `AccountBulkSerializer(data=[...], many=True)` |

## 4. Nested Serializer (Writable)

| Aspect | Details |
|---|---|
| **When to use** | Related objects must be created/updated in one request (e.g., order + line items) |
| **Pros** | Atomic creates, reduced API calls, self-contained payloads |
| **Cons** | Complex nested validation, deep nesting becomes unreadable, tight coupling |
| **Example** | `NestedTransactionSerializer` creates Transaction + Account + User in one call |

## 5. Nested Serializer (Read-only)

| Aspect | Details |
|---|---|
| **When to use** | Including related data in responses (e.g., user details in account detail) |
| **Pros** | Rich responses, no extra API calls for the client |
| **Cons** | Risk of N+1 queries (fix with `select_related`/`prefetch_related`) |
| **Example** | `AccountDetailSerializer` includes `user_details = UserSerializer(read_only=True)` |

## 6. Flat Serializer

| Aspect | Details |
|---|---|
| **When to use** | Simple input/output, mobile-friendly payloads, third-party API compatibility |
| **Pros** | Minimal payload size, easy to consume, simple validation |
| **Cons** | Repetitive across endpoints, loses relational structure |
| **Example** | `TransactionCreateSerializer(serializer.Serializer)` — just account_id + amount |

## Decision Flowchart

```
Is the data backed by a Django model?
├── NO  → Use Serializer (plain)
└── YES → Is it bulk/batch?
          ├── YES → Use ModelSerializer + ListSerializer
          └── NO  → Does it need related model data in the response?
                    ├── YES (read-only) → ModelSerializer + read-only nested
                    ├── YES (writable)  → Nested writable ModelSerializer
                    └── NO  → ModelSerializer (flat)
```

## When NOT to nest

- **Deep nesting** (>2 levels) — hard to validate, hard to debug
- **Performance-critical endpoints** — each nested level can multiply DB queries
- **Public APIs** — flat payloads are easier to document and version
- **When partial updates matter** — nested writable serializers force full replacement

## Quick Reference

| Serializer Type | Model Required | Auto Fields | Bulk Support | Nested Write |
|---|---|---|---|---|
| Serializer | No | No | Manual | Manual |
| ModelSerializer | Yes | Yes | Via ListSerializer | Manual override |
| ListSerializer | Depends | Depends | Yes | Via child |
| Nested Writeable | Yes | Yes | No | Yes |

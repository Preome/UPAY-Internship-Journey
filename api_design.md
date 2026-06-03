# API Design Document

## Overview
RESTful API for fintech operations — account management and transaction processing.
Built with Django REST Framework using ModelViewSet + DefaultRouter.

## Base URL
`http://localhost:8000/api/`

## Authentication
All endpoints require authentication. Two methods:
- **Basic Auth** — `Authorization: Basic <base64(username:password)>`
- **Session Auth** — login via `/api-auth/login/` (browsable API)

Test credentials: `testuser:test123` (primary), `admin:admin123`

---

## Endpoints

### Accounts

| Method | Endpoint | Description | Request Body | Response |
|--------|----------|-------------|--------------|----------|
| GET | `/accounts/` | List all accounts for logged-in user | None | Paginated array of accounts (list serializer) |
| POST | `/accounts/` | Create new account | `{"account_number": "ACC001", "account_type": "SAVINGS"}` | Created account (detail serializer) |
| GET | `/accounts/{id}/` | Get account details | None | Account object (detail serializer with user_name, transaction_count) |
| PUT | `/accounts/{id}/` | Full update | `{"account_number": "ACC001", "account_type": "CHECKING"}` | Updated account |
| PATCH | `/accounts/{id}/` | Partial update | `{"account_type": "BUSINESS"}` | Updated account |
| DELETE | `/accounts/{id}/` | Delete account | None | `204 No Content` |
| POST | `/accounts/{id}/freeze/` | Freeze account | `{"reason": "Fraud suspicion"}` | `{"status": "frozen", "account_id": 1, ...}` |
| GET | `/accounts/{id}/statement/` | Get statement (last 50 txns) | None | Account info + transactions array |

### Transactions

| Method | Endpoint | Description | Request Body | Response |
|--------|----------|-------------|--------------|----------|
| GET | `/transactions/` | List all transactions for user's accounts | None | Paginated array of transactions |
| POST | `/transactions/` | Create deposit/withdrawal/transfer | `{"account": 1, "transaction_type": "DEPOSIT", "amount": 100.00}` | Created transaction with auto-generated reference_number |
| GET | `/transactions/{id}/` | Get transaction details | None | Transaction object |
| POST | `/transactions/{id}/reverse/` | Reverse a transaction (within 24h) | `{"reason": "Incorrect amount"}` | Reversal status with original + reversal reference |

### Comparison Endpoints (DRF view style comparison)

| Method | Endpoint | View Style | Response Format |
|--------|----------|------------|-----------------|
| GET | `/api-compare/accounts-api/` | APIView | Plain JSON array (no pagination) |
| GET | `/api-compare/accounts-generic/` | GenericAPIView + Mixins | Paginated JSON (`count`, `results`) |

### Django Template Views

| Method | Endpoint | View Class | Description |
|--------|----------|------------|-------------|
| GET | `/django/accounts/` | ListView | HTML page listing accounts |
| GET | `/django/accounts/create/` | CreateView | Form to create account |
| GET/POST | `/django/accounts/{id}/update/` | UpdateView | Form to edit account |
| GET/POST | `/django/accounts/{id}/delete/` | DeleteView | Confirmation page to delete |
| GET | `/django/dashboard/` | TemplateView | Dashboard with stats |

---

## Request/Response Examples

### List Accounts
**Request:**
```http
GET /api/accounts/
Authorization: Basic dGVzdHVzZXI6dGVzdDEyMw==
```
**Response:** `200 OK`
```json
{
    "count": 2,
    "next": null,
    "previous": null,
    "results": [
        {
            "id": 4,
            "account_number": "ACC004",
            "account_type": "BUSINESS",
            "balance": "75000.00",
            "is_frozen": false
        },
        {
            "id": 3,
            "account_number": "ACC003",
            "account_type": "SAVINGS",
            "balance": "10000.00",
            "is_frozen": false
        }
    ]
}
```

### Create Account
**Request:**
```http
POST /api/accounts/
Authorization: Basic dGVzdHVzZXI6dGVzdDEyMw==
Content-Type: application/json

{
    "account_number": "ACC123456",
    "account_type": "SAVINGS"
}
```
**Response:** `201 Created`
```json
{
    "id": 5,
    "account_number": "ACC123456",
    "account_type": "SAVINGS",
    "balance": "0.00",
    "is_frozen": false,
    "user_name": "testuser",
    "created_at": "2026-06-03T05:50:45Z",
    "updated_at": "2026-06-03T05:50:45Z",
    "transaction_count": 0
}
```

### Get Account Detail
**Request:**
```http
GET /api/accounts/3/
Authorization: Basic dGVzdHVzZXI6dGVzdDEyMw==
```
**Response:** `200 OK`
```json
{
    "id": 3,
    "account_number": "ACC003",
    "account_type": "SAVINGS",
    "balance": "10000.00",
    "is_frozen": false,
    "user_name": "testuser",
    "created_at": "2026-06-03T05:48:24Z",
    "updated_at": "2026-06-03T05:48:24Z",
    "transaction_count": 1
}
```

### Update Account (PUT)
**Request:**
```http
PUT /api/accounts/3/
Authorization: Basic dGVzdHVzZXI6dGVzdDEyMw==
Content-Type: application/json

{
    "account_number": "ACC003",
    "account_type": "BUSINESS"
}
```
**Response:** `200 OK`
```json
{
    "id": 3,
    "account_number": "ACC003",
    "account_type": "BUSINESS",
    "balance": "10000.00",
    "is_frozen": false,
    "user_name": "testuser",
    "created_at": "2026-06-03T05:48:24Z",
    "updated_at": "2026-06-03T05:49:37Z",
    "transaction_count": 1
}
```

### Partial Update Account (PATCH)
**Request:**
```http
PATCH /api/accounts/3/
Authorization: Basic dGVzdHVzZXI6dGVzdDEyMw==
Content-Type: application/json

{
    "account_type": "SAVINGS"
}
```
**Response:** `200 OK`
```json
{
    "id": 3,
    "account_number": "ACC003",
    "account_type": "SAVINGS",
    "balance": "10000.00",
    "is_frozen": false,
    "user_name": "testuser",
    "created_at": "2026-06-03T05:48:24Z",
    "updated_at": "2026-06-03T05:49:40Z",
    "transaction_count": 1
}
```

### Delete Account
**Request:**
```http
DELETE /api/accounts/5/
Authorization: Basic dGVzdHVzZXI6dGVzdDEyMw==
```
**Response:** `204 No Content` (empty body)

### Freeze Account
**Request:**
```http
POST /api/accounts/3/freeze/
Authorization: Basic dGVzdHVzZXI6dGVzdDEyMw==
Content-Type: application/json

{
    "reason": "Suspicious activity detected"
}
```
**Response:** `200 OK`
```json
{
    "status": "frozen",
    "account_id": 3,
    "account_number": "ACC003",
    "reason": "Suspicious activity detected"
}
```
**Error (already frozen):** `400 Bad Request`
```json
{
    "error": "Account is already frozen"
}
```

### Get Account Statement
**Request:**
```http
GET /api/accounts/3/statement/
Authorization: Basic dGVzdHVzZXI6dGVzdDEyMw==
```
**Response:** `200 OK`
```json
{
    "account_id": 3,
    "account_number": "ACC003",
    "account_type": "SAVINGS",
    "current_balance": 10000.0,
    "is_frozen": false,
    "transactions": [
        {
            "id": 3,
            "transaction_type": "DEPOSIT",
            "amount": "10000.00",
            "description": "Salary deposit",
            "status": "COMPLETED",
            "reference_number": "TXN-USR00001",
            "created_at": "2026-06-03T05:48:24Z",
            "account": 3
        }
    ]
}
```

### List Transactions
**Request:**
```http
GET /api/transactions/
Authorization: Basic dGVzdHVzZXI6dGVzdDEyMw==
```
**Response:** `200 OK`
```json
{
    "count": 2,
    "next": null,
    "previous": null,
    "results": [
        {
            "id": 4,
            "transaction_type": "DEPOSIT",
            "amount": "75000.00",
            "description": "Business funding",
            "status": "COMPLETED",
            "reference_number": "TXN-USR00002",
            "created_at": "2026-06-03T05:48:24Z",
            "account": 4
        },
        {
            "id": 3,
            "transaction_type": "DEPOSIT",
            "amount": "10000.00",
            "description": "Salary deposit",
            "status": "COMPLETED",
            "reference_number": "TXN-USR00001",
            "created_at": "2026-06-03T05:48:24Z",
            "account": 3
        }
    ]
}
```

### Create Transaction (Deposit)
**Request:**
```http
POST /api/transactions/
Authorization: Basic dGVzdHVzZXI6dGVzdDEyMw==
Content-Type: application/json

{
    "account": 3,
    "transaction_type": "DEPOSIT",
    "amount": 500.00,
    "description": "Salary deposit"
```
**Response:** `201 Created`
```json
{
    "id": 5,
    "transaction_type": "DEPOSIT",
    "amount": "500.00",
    "description": "Salary deposit",
    "status": "COMPLETED",
    "reference_number": "TXN-A1B2C3D4E5",
    "created_at": "2026-06-03T05:49:53Z",
    "account": 3
}
```

### Create Transaction (Withdrawal)
**Request:**
```http
POST /api/transactions/
Authorization: Basic dGVzdHVzZXI6dGVzdDEyMw==
Content-Type: application/json

{
    "account": 4,
    "transaction_type": "WITHDRAWAL",
    "amount": 200.00,
    "description": "ATM withdrawal"
```
**Response:** `201 Created`
```json
{
    "id": 6,
    "transaction_type": "WITHDRAWAL",
    "amount": "200.00",
    "description": "ATM withdrawal",
    "status": "COMPLETED",
    "reference_number": "TXN-F6E7D8C9B0",
    "created_at": "2026-06-03T05:51:00Z",
    "account": 2
}
```

### Create Transaction (Transfer)
**Request:**
```http
POST /api/transactions/
Authorization: Basic dGVzdHVzZXI6dGVzdDEyMw==
Content-Type: application/json

{
    "account": 3,
    "transaction_type": "TRANSFER",
    "amount": 1000.00,
    "description": "Fund transfer"
```
**Response:** `201 Created`
```json
{
    "id": 7,
    "transaction_type": "TRANSFER",
    "amount": "1000.00",
    "description": "Fund transfer",
    "status": "COMPLETED",
    "reference_number": "TXN-1A2B3C4D5E",
    "created_at": "2026-06-03T05:51:30Z",
    "account": 3
}
```

### Get Transaction Detail
**Request:**
```http
GET /api/transactions/3/
Authorization: Basic dGVzdHVzZXI6dGVzdDEyMw==
```
**Response:** `200 OK`
```json
{
    "id": 3,
    "transaction_type": "DEPOSIT",
    "amount": "10000.00",
    "description": "Salary deposit",
    "status": "COMPLETED",
    "reference_number": "TXN-USR00001",
    "created_at": "2026-06-03T05:48:24Z",
    "account": 3
}
```

### Reverse Transaction
**Request:**
```http
POST /api/transactions/3/reverse/
Authorization: Basic dGVzdHVzZXI6dGVzdDEyMw==
Content-Type: application/json

{
    "reason": "Customer requested reversal - incorrect amount"
}
```
**Response:** `200 OK`
```json
{
    "status": "reversed",
    "original_transaction": "TXN-USR00001",
    "reversal_transaction": "REV-TXN-USR00001",
    "message": "Transaction reversed successfully. Reason: Customer requested reversal - incorrect amount"
}
```
**Error (already reversed):** `400 Bad Request`
```json
{
    "error": "Transaction already reversed"
}
```
**Error (older than 24h):** `400 Bad Request`
```json
{
    "error": "Cannot reverse transactions older than 24 hours"
}
```
**Error (no reason):** `400 Bad Request`
```json
{
    "error": "Reason is required for reversal"
}
```

---

## Authentication Errors

### Missing Credentials
```json
{
    "detail": "Authentication credentials were not provided."
}
```

### Invalid Credentials
```json
{
    "detail": "Invalid username/password."
}
```

---

## Bugs Found & Fixed

| # | Bug | Endpoint | Root Cause | Fix |
|---|-----|----------|------------|-----|
| 1 | `NOT NULL constraint failed: accounts_account.user_id` | `POST /api/accounts/` | `AccountViewSet` didn't set `user` on create | Added `perform_create` to set `user=self.request.user` |
| 2 | `NameError: name 'models' is not defined` | `/django/accounts/` (ListView) | `views_django.py` used `models.Sum()` without importing `Sum` from `django.db.models` | Added `from django.db.models import Sum` |
| 3 | `NoReverseMatch` for `'account_list'` | Django CreateView/UpdateView/DeleteView | URL name was `django_account_list`, but views used `reverse_lazy('account_list')` | Changed to `reverse_lazy('django_account_list')` |
| 4 | TemplateNotFound: `account_list.html` | `/django/accounts/` (ListView) | File was `accounts_list.html` (plural) but template_name was `account_list.html` (singular) | Changed to `template_name = 'accounts_list.html'` |
| 5 | Missing templates | CreateView/UpdateView/DeleteView | `account_form.html` and `account_confirm_delete.html` didn't exist | Created both templates |
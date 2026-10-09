# Paid Link Backend API Contract

This document describes the HTTP API registered by the Django backend. Unless stated otherwise, requests and responses use JSON (`Content-Type: application/json`). Monetary values are decimal strings to avoid client-side floating point rounding. Timestamps are ISO-8601 strings (UTC unless an offset is shown).

Base paths below are relative to the deployed backend origin. Trailing slashes are part of every route. There is no version prefix yet; clients should centralize the base URL and route strings so a future versioned API can be adopted cleanly.

## Authentication

- Authentication is JWT bearer authentication. Send `Authorization: Bearer <access>` on protected calls. JSON APIs are usable by browser and mobile clients; mobile clients do not need cookies or a browser `Origin` header.
- `POST /api/accounts/register/` accepts `{ "username", "email", "password", "phone_number" }`; password must be at least 8 characters. Registration creates a learner and returns `{ "message", "user": { "id", "username", "email", "role", "credits" }, "tokens": { "refresh", "access" } }` (201). Role is not client-selectable.
- `POST /api/accounts/login/` accepts `{ "username", "password" }`; SimpleJWT returns `{ "refresh", "access" }` (200).
- `POST /api/accounts/token/refresh/` accepts `{ "refresh" }`; returns `{ "access" }` and, if rotation is enabled later, may also include a refresh token. The current configuration uses SimpleJWT defaults; refresh rotation is not enabled explicitly.
- Missing, malformed, invalid, or expired access tokens produce 401. Authenticated users lacking the required role generally receive 403. SimpleJWT and DRF errors use `{"detail": ...}`; many hand-written endpoints use `{"error": ...}`; field validation errors are field-keyed. This shape is retained for compatibility.
- Registration and profile output include the user's current credit balance. Do not treat a client-side balance as authoritative; reread it from the API after financial actions.

## Pagination and query conventions

Paginated endpoints return DRF's shape: `{"count": N, "next": URL|null, "previous": URL|null, "results": [...]}`. Creator transaction/withdrawal histories and admin lists accept `page` and `page_size`; default size is 50 and maximum is 100. Admin list filtering uses the parameters shown below. Public content and creator content lists are currently unpaginated arrays. No global pagination setting is configured.

## Endpoint index

`Learner` and `Creator` refer to `UserProfile.role`. `Admin` means that same role is `admin`; Django staff/superuser status alone does not grant access to the custom admin API. Callback endpoints are server-to-server endpoints and do not use user JWT authentication; they require the per-record callback token in the query string.

### Health

| Method and endpoint | Authentication/role | Request | Success |
|---|---|---|---|
| `GET /api/health/` | Public | None | 200 `{"status":"ok"}` if database probe succeeds; 503 `{"status":"unavailable"}` otherwise. No settings, credentials, or exception text are returned. |

### Accounts and creator earnings

| Method and endpoint | Authentication/role | Request | Success |
|---|---|---|---|
| `POST /api/accounts/register/` | Public | JSON: `username`, `email`, `password` (min 8 chars), `phone_number` | 201 registration envelope described above. |
| `POST /api/accounts/login/` | Public | JSON: `username`, `password` | 200 `{refresh, access}`. |
| `POST /api/accounts/token/refresh/` | Public with valid refresh token | JSON: `refresh` | 200 `{access}`. |
| `GET /api/accounts/profile/` | Any authenticated role | None | 200 `{id, username, email, phone_number, role, credits, is_verified}`. |
| `GET /api/accounts/creator/earnings/summary/` | Creator or admin; data is scoped to caller | None | 200 `{total_sales_count, gross_earnings, available_credit_balance, total_withdrawn, pending_processing_withdrawal_amount, published_contents_count}`. Monetary fields are strings. |
| `GET /api/accounts/creator/earnings/content/` | Creator or admin; scoped to caller | None | 200 array of `{content_id, title, price, purchase_count, gross_sales, latest_purchase_at}` (includes zero-sales content). |
| `GET /api/accounts/creator/transactions/` | Creator or admin; ledger scoped to caller | `page`, `page_size` | Paginated results `{id, transaction_type, amount, balance_after, description, timestamp, idempotency_key}`. |
| `GET /api/accounts/creator/withdrawals/` | Creator or admin; withdrawals scoped to caller | `page`, `page_size` | Paginated results with amount, status, payout status, masked phone, timestamps, failure/discrepancy fields. Callback and reconciliation tokens are omitted. |

The creator endpoints permit an admin role, but still return only the authenticated admin's own creator-scoped records (normally none). Use `/api/admin/` for platform-wide administration.

### Content

Content response fields are `id`, `creator`, `creator_username`, `title`, `description`, `content_type` (`pdf` or `video`), `price`, `thumbnail_url`, `is_published`, `created_at`, `updated_at`. Protected file identifiers and file URLs are omitted from ordinary content serialization.

| Method and endpoint | Authentication/role | Request | Success |
|---|---|---|---|
| `GET /api/content/` | Public | None | 200 unpaginated array of published content objects. |
| `POST /api/content/create/` | Creator or admin | Multipart form: required `title`, `description`, `content_type`, `price`, `file`; optional `thumbnail_url`, `is_published` (`true`/`false`) | 201 `{message, content}`. File is uploaded to configured storage. |
| `GET /api/content/my-content/` | Creator or admin | None | 200 unpaginated content array scoped to caller (admin sees their own content through this route). |
| `PATCH /api/content/<content_id>/update/` | Creator or admin; creator owns item, admin can update any | JSON subset of `title`, `description`, `price`, `thumbnail_url`, `is_published` | 200 `{message, content}`. |
| `PATCH /api/content/<content_id>/publish/` | Creator or admin; creator owns item, admin can update any | JSON `{ "is_published": true|false }` (string values also accepted) | 200 `{message, content}`. |
| `GET /api/content/<content_id>/access/` | Any authenticated user who purchased it | None | 200 `{message, content: {id, title, content_type, file_url}}`; `file_url` is a time-limited/private delivery URL. |

### Purchases

| Method and endpoint | Authentication/role | Request | Success |
|---|---|---|---|
| `POST /api/purchases/<content_id>/purchase/` | Any authenticated user | Empty JSON body | 201 `{message, purchase: {content_id, title, amount_paid}, remaining_credits}`. Insufficient credits, unavailable content, or already-purchased conditions return 400/404 as applicable. |

### Payments and withdrawals

| Method and endpoint | Authentication/role | Request | Success |
|---|---|---|---|
| `POST /api/payments/mpesa/initiate/` | Any authenticated user | JSON `{amount, phone_number}`; valid whole-KES amount and Kenyan phone required | 201 `{payment_id, status, checkout_request_id}`; uncertain provider response returns 202 `{payment_id, status, message}`. This endpoint initiates a real provider operation when configured. |
| `POST /api/payments/withdrawals/request/` | Creator only | JSON `{amount, phone_number}` | 201 `{withdrawal: {id, amount, phone_number, status}}`; reserves are not made until admin approval. |
| `GET /api/payments/withdrawals/` | Admin role | None | 200 `{withdrawals: [...]}`. Legacy unpaginated admin list; phone numbers are currently unmasked on this legacy route. Prefer `/api/admin/withdrawals/`. |
| `POST /api/payments/withdrawals/<withdrawal_id>/approve/` | Admin role | Empty body | 200 `{message, withdrawal_id, status, remaining_credits}`; reserves balance using the financial service. |
| `POST /api/payments/withdrawals/<withdrawal_id>/submit/` | Admin role | Empty body | Submits a B2C payout and returns 202 `{status, conversation_id}` or uncertain status. This is an explicit external payment action; clients must never automatically retry uncertain submissions. |
| `POST /api/payments/withdrawals/<withdrawal_id>/cancel/` | Admin role | Empty body | 200 `{status, remaining_credits}` if pending/releasable reservation; otherwise 400. |
| `POST /api/payments/withdrawals/<withdrawal_id>/reconcile/` | Admin role | Empty body | 202 `{status, message, provider_response}` on accepted provider status query; does not resubmit payout. |
| `POST /api/payments/mpesa/payments/<payment_id>/reconcile/` | Admin role | Empty body | 200 `{status:"completed"}` if already completed or newly reconciled; unresolved results return 202 `{status, message}`. |
| `POST /api/payments/mpesa/callback/?callback_token=...` | Provider callback URL; callback token required | Daraja STK callback JSON (`Body.stkCallback`) | Provider protocol `{ResultCode, ResultDesc}`. Callback is not itself proof of payment; independent verification is required before credit. |
| `POST /api/payments/mpesa/b2c/result/?callback_token=...` | Provider callback URL; callback token required | B2C result JSON | Provider protocol `{ResultCode, ResultDesc}`. Initial result only records event/unknown outcome; reconciliation callback must correlate and verify before settlement. |
| `POST /api/payments/mpesa/b2c/result/?reconciliation=1&callback_token=...` | Provider status callback; per-query reconciliation token required | Transaction-status result JSON | Provider protocol acknowledgment. Verified result may settle only when provider IDs, amount/recipient/receipt checks pass. |
| `POST /api/payments/mpesa/b2c/timeout/?callback_token=...` | Provider callback URL; callback token required | B2C timeout JSON | Provider protocol `{ResultCode}`; uncertain outcomes remain unresolved. |

Callback tokens are bearer credentials embedded in callback URLs. Never expose them in a frontend response, analytics, browser history, or logs. Only the backend should configure provider callback URLs.

### Admin management and monitoring

All endpoints below require authenticated `UserProfile.role=admin`. List responses use the pagination envelope above; page size defaults to 50, maximum 100. Supported common query parameters: `page`, `page_size`, `search` where listed, and exact-match filters below. Detail requests return a single object. Tokens, password hashes, provider credentials, provider callback payloads, and internal transaction identifiers are excluded unless explicitly shown.

| Method and endpoint | Query parameters | Successful response fields |
|---|---|---|
| `GET /api/admin/dashboard/` | None | `{total_users, learners, creators, published_content, total_purchases, total_purchase_value, pending_withdrawals, unresolved_payment_records}`. |
| `GET /api/admin/users/`, `GET /api/admin/users/<id>/` | List: `search`, `role`, `is_active` | `{id, username, email, first_name, last_name, is_active, date_joined, role, phone_number (masked), credits, is_verified}`. |
| `GET /api/admin/creators/`, `GET /api/admin/creators/<id>/` | List: `search` | User fields above, only creator role. |
| `GET /api/admin/learners/`, `GET /api/admin/learners/<id>/` | List: `search` | User fields above, only learner role. |
| `GET /api/admin/content/`, `GET /api/admin/content/<id>/` | List: `search`, `creator`, `is_published`, `content_type` | `{id, creator_username, title, description, content_type, price, thumbnail_url, is_published, created_at, updated_at}`. File URLs and storage IDs omitted. |
| `GET /api/admin/purchases/`, `GET /api/admin/purchases/<id>/` | List: `search`, `user`, `content` | `{id, user_username, content_title, amount_paid, purchased_at}`. |
| `GET /api/admin/ledger/` | `search`, `user`, `transaction_type` | `{id, user_username, transaction_type, amount, balance_after, description, created_at, idempotency_key}`. |
| `GET /api/admin/withdrawals/`, `GET /api/admin/withdrawals/<id>/` | List: `search`, `creator`, `status`, `payout_status` | `{id, creator_username, amount, status, payout_status, phone_number (masked), approved_by_username, approved_at, created_at, updated_at, failure_reason, callback_discrepancy, refund_recorded_at, provider_failure_verified_at}`. |
| `POST /api/admin/withdrawals/<id>/approve/` | None | Uses existing approval service; 200 with reserved status and remaining balance. Invalid state/insufficient balance returns 400. |
| `POST /api/admin/withdrawals/<id>/cancel/` | None | Uses existing cancel/release state machine; 200 with status and remaining balance, otherwise 400. |
| `POST /api/admin/withdrawals/<id>/reconcile/` | None | Existing provider reconciliation; does not retry payout. Returns 202 while unresolved. |
| `POST /api/admin/payments/<id>/reconcile/` | None | Existing STK provider verification/reconciliation; unresolved returns 202. |

## Common error responses

| HTTP status | Meaning and typical shape |
|---|---|
| 400 | Invalid input or disallowed state, generally `{"error":"..."}`; DRF field errors may be field-keyed. |
| 401 | Missing, malformed, expired, or invalid JWT; typically `{"detail":"Authentication credentials were not provided."}` or token-specific detail. |
| 403 | Authenticated caller lacks role, owns no access, or callback token invalid; shape varies between `error`, `detail`, and callback protocol. |
| 404 | Resource absent/unavailable; typically `{"error":"..."}` or DRF `detail`. |
| 202 | Provider result remains unresolved or reconciliation is pending. Do not interpret as paid/failed and do not automatically retry a payout. |
| 500 | Production `DEBUG=False` should suppress Django tracebacks. Unexpected provider/configuration details must not be returned to clients. |

## CORS, CSRF, and mobile clients

Set `CORS_ALLOWED_ORIGINS` to the exact React web origins (comma-separated, including scheme and port). `CORS_ALLOW_CREDENTIALS` defaults to false. JWT is sent in the Authorization header; browser clients should not depend on session cookies. Cross-origin authorization headers require a successful preflight. Mobile clients are not subject to browser CORS and should use HTTPS plus the same bearer token. `CSRF_TRUSTED_ORIGINS` is for browser/session flows such as Django admin, not a substitute for JWT or CORS configuration. Configure the web origin with `VITE_API_BASE_URL` and the mobile origin with `EXPO_PUBLIC_API_BASE_URL`; both values are the API origin only, without an `/api` path. Development examples are in each frontend's `.env.example`.

## Integration cautions and known contract limitations

- No global pagination is configured; only the histories and admin management lists paginate. Public content and creator-content lists can grow without bound.
- Response error envelopes are not globally uniform (`error`, `detail`, validation maps, and provider callback acknowledgments). Clients should parse status first and tolerate these current shapes.
- `GET /api/payments/withdrawals/` is a legacy duplicate admin list separate from `/api/admin/withdrawals/`; it is unpaginated and returns the unmasked phone. Prefer the new `/api/admin/` endpoint. The legacy route remains for compatibility.
- `/api/payments/withdrawals/<id>/submit/` can initiate B2C payment. It must only be called by an explicitly authorized operator workflow, never by learner/creator frontends or automatic retry logic.
- Callback tokens appear in callback query strings by design. Configure web-server/access logs to redact `callback_token`; do not pass callback URLs to browsers.
- Runtime CORS and security values come from environment configuration. No credential values are documented here. Production must set `DEBUG=False`, `ALLOWED_HOSTS`, `CORS_ALLOWED_ORIGINS`, trusted HTTPS proxy behavior if applicable, and the correct HTTPS origins.

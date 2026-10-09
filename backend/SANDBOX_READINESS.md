# Paid Link sandbox and deployment configuration

This file documents configuration names only. Put credentials in the deployment secret manager or protected environment; do not commit secret values.

## Django and browser security

Set `DEBUG=False` for any hosted sandbox or production deployment. The code default is false, but an explicit environment value overrides it. Configure `ALLOWED_HOSTS` as a comma-separated host allowlist, `CORS_ALLOWED_ORIGINS` as comma-separated complete origins such as `https://frontend.example`, and `CSRF_TRUSTED_ORIGINS` as the trusted scheme+host origins. CORS credentials default off; only enable `CORS_ALLOW_CREDENTIALS` when required.

When `DEBUG=False`, HTTPS redirect, HSTS for one year, HSTS subdomains/preload, and secure session/CSRF cookies default on. Set `SECURE_SSL_REDIRECT`, `SECURE_HSTS_SECONDS`, `SECURE_HSTS_INCLUDE_SUBDOMAINS`, `SECURE_HSTS_PRELOAD`, `SESSION_COOKIE_SECURE`, and `CSRF_COOKIE_SECURE` explicitly if deployment needs different values. Behind a TLS-terminating proxy, set `USE_X_FORWARDED_PROTO=True` only when that proxy strips incoming forwarded headers and sets its own trusted `X-Forwarded-Proto: https` value. Configure `CSRF_TRUSTED_ORIGINS` for any session-authenticated browser admin flow.

`SECRET_KEY` must come from a secret manager or protected environment. Never use `.env` as a committed deployment artifact.

The application logging filter redacts `callback_token` query parameter values from Django application log messages. Reverse proxies, load balancers, WSGI servers, APM agents, and CDN access logs are outside Django's logging configuration: configure them to omit or redact the `callback_token` query parameter. Callback URLs are bearer credentials and must not be included in analytics, traces, error reports, or referrer data.

## M-Pesa environment variables

`MPESA_ENVIRONMENT` accepts `sandbox` (default) or `production`. The selected host is used for OAuth, STK, B2C, and transaction-status requests. Do not set it to `production` during sandbox work.

| Variable | Purpose |
|---|---|
| `MPESA_CONSUMER_KEY` | Daraja OAuth client key |
| `MPESA_CONSUMER_SECRET` | Daraja OAuth client secret |
| `MPESA_SHORTCODE` | STK business shortcode |
| `MPESA_PASSKEY` | STK password generation |
| `MPESA_CALLBACK_URL` | Public HTTPS endpoint `/api/payments/mpesa/callback/` |
| `MPESA_B2C_INITIATOR_NAME` | B2C and transaction-status initiator |
| `MPESA_B2C_SECURITY_CREDENTIAL` | Encrypted B2C/status-query credential |
| `MPESA_B2C_SHORTCODE` | B2C/status-query shortcode |
| `MPESA_B2C_RESULT_URL` | Public HTTPS endpoint `/api/payments/mpesa/b2c/result/` |
| `MPESA_B2C_TIMEOUT_URL` | Public HTTPS endpoint `/api/payments/mpesa/b2c/timeout/` |
| `MPESA_B2C_RECONCILIATION_URL` | Public HTTPS endpoint `/api/payments/mpesa/b2c/result/`; reconciliation appends `reconciliation=1` and a per-query bearer token |

Callback URLs must preserve query strings exactly. Configure the callback host, TLS certificate, route forwarding, body size limits, and provider allowlisting as required by the deployment. Verify the Daraja sandbox status-query result fields against the values expected by the reconciliation handlers before enabling customer-facing requests.

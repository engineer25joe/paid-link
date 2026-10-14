# ElimuBang

ElimuBang is a single Git monorepo containing the existing Django REST API and its two clients:

- `backend/` — Django REST Framework API and PostgreSQL configuration
- `frontend/web/` — React and Vite web client
- `frontend/mobile/` — React Native and Expo SDK 57 app (JavaScript)

The official web and mobile identity is **ElimuBang — Quality Tuition for a Brighter You.** The supplied logo lives at `frontend/web/public/elimu-bang-logo.png`; mobile icon, adaptive icon, and splash image files are generated from that original while preserving its full aspect ratio. Existing iOS and Android application identifiers are retained.

The clients call the same API; registration remains implemented by Django at `POST /api/accounts/register/`. It returns the documented user and JWT envelope in [the API contract](backend/API_CONTRACT.md).

## Local setup

Use PostgreSQL for the backend and Node.js with npm for either client. Copy `backend/.env.example` to `backend/.env`, set local database values and a local-only `SECRET_KEY`, then install the backend requirements and start Django:

```sh
cd backend
python -m venv .venv
# Activate .venv for your shell, then:
python -m pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

In another terminal, copy `frontend/web/.env.example` to `frontend/web/.env`, set `VITE_API_BASE_URL=http://127.0.0.1:8000`, and run `npm ci && npm run dev` from `frontend/web/`. The web client posts registration JSON to `POST /api/accounts/register/`. Production builds require an HTTPS API origin and never default to localhost.

For the Expo client, copy `frontend/mobile/.env.example` to `frontend/mobile/.env`, set `EXPO_PUBLIC_API_BASE_URL` to the API origin, then run `npm ci && npm start` in `frontend/mobile/`. A physical device needs the development computer's LAN address; a production EAS build needs the deployed HTTPS origin and the pre-install hook validates that configuration.

The mobile client stores JWTs with Expo SecureStore, validates the session against the profile API, and exposes role-specific learner, creator, and administrator navigation from the server-reported role. Learners can search the public catalogue, view details, purchase with existing credits, review their own purchases, and request protected resource links from the backend. Creators can list, edit, publish/unpublish, upload supported PDF/video files, and view server-reported earnings. Administrator mobile management screens are read-only and call the protected admin API. Wallet top-up initiation uses the existing backend payment endpoint.

Purchase history is returned only for the authenticated account and includes no private file URL. The backend still issues short-lived protected resource links only after verifying purchase access. File replacement during content editing is not offered because the existing update endpoint accepts metadata only.

### Environment variables

- Backend: `SECRET_KEY`, `DEBUG`, `DATABASE_URL` (or `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT`), `ALLOWED_HOSTS`, `CORS_ALLOWED_ORIGINS`, `CORS_ALLOW_CREDENTIALS`, and `CSRF_TRUSTED_ORIGINS`. Use complete comma-separated origins, including scheme and port. The JWT API does not require credentialed CORS.
- Optional integrations: `CLOUDINARY_CLOUD_NAME`, `CLOUDINARY_API_KEY`, `CLOUDINARY_API_SECRET`, and the `MPESA_*` settings shown in `backend/.env.example`. Keep payment integration in sandbox until separately configured; no CI or deployment workflow performs transactions.
- Web: `VITE_API_BASE_URL` is only the backend origin, without `/api`.
- Mobile: `EXPO_PUBLIC_API_BASE_URL` is only the backend origin, without `/api`.

Keep actual `.env` files and credentials out of Git. Tracked `.env.example` files contain placeholders only.

## Render deployment

The existing live frontend is `https://paidlinkweb.onrender.com` and the existing API is `https://paid-link-backend.onrender.com`. Deploy the web bundle through the already-created Render Static Site: use `frontend/web` as the root directory, `npm ci && npm run build` as the build command, and `dist` as the publish directory. Set that static site's `VITE_API_BASE_URL` to `https://paid-link-backend.onrender.com` and retain its `/*` to `/index.html` rewrite for client-side routes. Confirm the existing backend CORS setting includes `https://paidlinkweb.onrender.com` before publishing.

Do not apply the root [Render Blueprint](render.yaml) to this existing deployment: it declares a PostgreSQL resource and would provision a separate database. Keep the production database and secrets unchanged. The API's pre-deploy migration and optional provisioning command should only run through the already-configured backend service's normal deployment process; do not create or reset a database as part of a frontend update. No deployment is initiated by local builds.

## CI and monitoring

GitHub Actions CI runs non-payment Django tests against PostgreSQL, builds the web production bundle, and checks Expo SDK/package compatibility. Payment integration tests are excluded; no real M-Pesa or other payment request is made.

The [keep-alive workflow](.github/workflows/keep-alive.yml) requests the API health URL every ten minutes and also supports manual runs. To configure it once, open the GitHub repository's **Settings → Secrets and variables → Actions → Variables**, add a repository variable named `BACKEND_HEALTH_URL`, and set it to `https://paid-link-backend.onrender.com/api/health/` (or the health URL for your deployment). The workflow reports a missing variable, timeout, invalid response, or unhealthy HTTP response as a failed run; inspect it in the Actions tab. Scheduled Actions may be delayed or disabled by GitHub, and periodic requests do not guarantee service uptime or prevent every hosting provider from sleeping a service.

For local checks, run `npm test` and `npm run build` in `frontend/web`, and `npm run check` plus `npx expo export --platform android` in `frontend/mobile`. Django checks and tests need the pinned dependencies and an isolated PostgreSQL test database; financial concurrency tests are not representative on SQLite.

## Initial Django administrator

The `provision_superuser` management command is opt-in and idempotent. It reads `DJANGO_SUPERUSER_ENABLED`, `DJANGO_SUPERUSER_USERNAME`, `DJANGO_SUPERUSER_EMAIL`, and `DJANGO_SUPERUSER_PASSWORD`. The password must be at least 14 characters and pass Django's configured password validators. With provisioning disabled or the enable variable absent, the command exits without creating an account. It never changes an existing password; a non-superuser username or conflicting email causes a safe error.

For a first Render setup, add those values to the existing backend service's protected environment settings. Keep `DJANGO_SUPERUSER_ENABLED=true` only for the deployment that runs the command, then remove the password and turn provisioning off after the account has been created. The existing backend deployment must have a controlled pre-deploy command containing `python manage.py migrate --noinput && python manage.py provision_superuser`; the command must execute in the backend service environment, after migrations and before serving traffic. Render does not execute a management command merely because the environment variables exist. If the existing service does not have a pre-deploy hook, configure that command through the service's supported deployment settings before triggering a deployment. This repository's `render.yaml` describes a separate database, so do not sync it to the existing production service. No production account was provisioned by this code change.

Application login uses the existing JWT endpoint. A Django superuser's profile is reported by the API with the trusted `admin` role even if its stored profile role is `learner`; the Django admin site continues using Django session authentication. The `/admin/` Django site remains a separate, normal Django login.

Creator applications are submitted at `/api/accounts/creator/applications/`; admins review them at `/api/admin/creator-applications/` and can create a creator account at `/api/admin/creators/create/`. Direct creator creation requires an initial password in the protected admin interface; the API stores only Django's password hash. The account setup/reset email flow is not configured in this project.

The wallet shows ledger entries and M-Pesa payment states. Top-up requests use the existing server-side provider initiation and callback reconciliation. Credits are added only after the backend verifies a payment with Daraja. Configure provider credentials and callback URLs in Render before enabling real use; this task did not initiate a transaction.

## Troubleshooting registration

`Failed to fetch` is a browser network/CORS failure rather than a Django validation response. The registration code sends JSON to `/api/accounts/register/`; the route and request body match the Django API contract. In production, the most likely configuration cause is the web bundle having a missing or incorrect `VITE_API_BASE_URL` (the visitor's browser then cannot reach the intended API). A second common cause is `CORS_ALLOWED_ORIGINS` not containing the exact web origin. Confirm the deployed web build uses the API origin only, the API is reachable at `/api/health/`, and CORS matches the browser address exactly, including `https://` and any custom domain. Registration uses JWT and does not need cookie credentials or a CSRF token.

For local development, confirm Django and PostgreSQL are running, the web `.env` points to the Django origin, and Django's `CORS_ALLOWED_ORIGINS` contains the local Vite origin (usually `http://localhost:5173`). Use the browser Network tab to distinguish a refused request from a failed CORS preflight. API validation errors are returned as JSON and shown in the form; network and CORS failures do not produce that JSON response.

## Safe Git contents

The root `.gitignore` excludes local environments, credentials, database data/dumps, dependency folders, build output, coverage, logs, and editor/OS files. Placeholder-only `.env.example` files remain tracked.

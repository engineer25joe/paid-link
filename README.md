# Paid Link

Paid Link is a single Git monorepo containing the existing Django REST API and its two clients:

- `backend/` — Django REST Framework API and PostgreSQL configuration
- `frontend/web/` — React and Vite web client
- `frontend/mobile/` — React Native and Expo SDK 57 app

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

### Environment variables

- Backend: `SECRET_KEY`, `DEBUG`, `DATABASE_URL` (or `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT`), `ALLOWED_HOSTS`, `CORS_ALLOWED_ORIGINS`, `CORS_ALLOW_CREDENTIALS`, and `CSRF_TRUSTED_ORIGINS`. Use complete comma-separated origins, including scheme and port. The JWT API does not require credentialed CORS.
- Optional integrations: `CLOUDINARY_CLOUD_NAME`, `CLOUDINARY_API_KEY`, `CLOUDINARY_API_SECRET`, and the `MPESA_*` settings shown in `backend/.env.example`. Keep payment integration in sandbox until separately configured; no CI or deployment workflow performs transactions.
- Web: `VITE_API_BASE_URL` is only the backend origin, without `/api`.
- Mobile: `EXPO_PUBLIC_API_BASE_URL` is only the backend origin, without `/api`.

Keep actual `.env` files and credentials out of Git. Tracked `.env.example` files contain placeholders only.

## Render deployment

The root [Render Blueprint](render.yaml) provisions PostgreSQL, the Django API, and the static React app as one monorepo deployment. The API installs `backend/requirements.txt`, collects static files, runs `python manage.py migrate --noinput` as its pre-deploy step, and starts Gunicorn. Render probes `/api/health/`, which returns only `{"status":"ok"}` after a database connectivity check or a generic 503 response.

The Blueprint generates `SECRET_KEY` and reads database connection details from its managed database. Optional Cloudinary and M-Pesa values are `sync: false` dashboard inputs; configure them only if those integrations are needed. No credential values belong in this repository. The web build is configured with `VITE_API_BASE_URL=https://paid-link-api.onrender.com`, and backend CORS allows `https://paid-link-web.onrender.com`. If you use different Render service names or custom domains, update both origins and `ALLOWED_HOSTS` in the Blueprint. Review the Blueprint and deploy in Render to enable deployment automation.

## CI and monitoring

GitHub Actions CI runs non-payment Django tests against PostgreSQL, builds the web production bundle, and checks Expo SDK/package compatibility. Payment integration tests are excluded; no real M-Pesa or other payment request is made.

The [keep-alive workflow](.github/workflows/keep-alive.yml) requests the API health URL every ten minutes and also supports manual runs. To configure it once, open the GitHub repository's **Settings → Secrets and variables → Actions → Variables**, add a repository variable named `BACKEND_HEALTH_URL`, and set it to `https://paid-link-api.onrender.com/api/health/` (or the health URL for your deployment). The workflow reports a missing variable, timeout, invalid response, or unhealthy HTTP response as a failed run; inspect it in the Actions tab. Scheduled Actions may be delayed or disabled by GitHub, and periodic requests do not guarantee service uptime or prevent every hosting provider from sleeping a service.

## Troubleshooting registration

`Failed to fetch` is a browser network/CORS failure rather than a Django validation response. The registration code sends JSON to `/api/accounts/register/`; the route and request body match the Django API contract. In production, the most likely configuration cause is the web bundle having a missing or incorrect `VITE_API_BASE_URL` (the visitor's browser then cannot reach the intended API). A second common cause is `CORS_ALLOWED_ORIGINS` not containing the exact web origin. Confirm the deployed web build uses the API origin only, the API is reachable at `/api/health/`, and CORS matches the browser address exactly, including `https://` and any custom domain. Registration uses JWT and does not need cookie credentials or a CSRF token.

For local development, confirm Django and PostgreSQL are running, the web `.env` points to the Django origin, and Django's `CORS_ALLOWED_ORIGINS` contains the local Vite origin (usually `http://localhost:5173`). Use the browser Network tab to distinguish a refused request from a failed CORS preflight. API validation errors are returned as JSON and shown in the form; network and CORS failures do not produce that JSON response.

## Safe Git contents

The root `.gitignore` excludes local environments, credentials, database data/dumps, dependency folders, build output, coverage, logs, and editor/OS files. Placeholder-only `.env.example` files remain tracked.

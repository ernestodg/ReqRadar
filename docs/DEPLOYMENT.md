# Deployment

## Backend on Railway

1. Create a PostgreSQL database.
2. Set `DATABASE_URL`.
3. Set `APP_ENV=production`.
4. Set `DEV_AUTH_BYPASS=false`.
5. Set `SUPABASE_URL` to the Supabase project URL. The API derives the issuer and JWKS URL from this value.
6. Set `FRONTEND_ORIGIN` to the exact deployed frontend origin, for example `https://reqradar.pages.dev`.
7. Set `ALLOWED_HOSTS` to the exact Railway API host or custom API domain. Do not use `*` in production.
8. Deploy `backend/Dockerfile`.
9. Run `alembic upgrade head` before serving traffic. The current container command performs this during startup; for production release windows, prefer a Railway pre-deploy migration step followed by the web process start.

## Frontend on Cloudflare Pages

1. Set project root to `frontend`.
2. Build command: `npm ci && npm run build`.
3. Output directory: `dist`.
4. Set `VITE_API_URL` to the deployed API origin.
5. Set `VITE_SUPABASE_URL` and `VITE_SUPABASE_ANON_KEY` for Supabase Auth.
6. For Phase 4 beta telemetry, set browser-safe observability values only:
   - `VITE_TELEMETRY_ENABLED=true`
   - `VITE_POSTHOG_KEY`
   - `VITE_POSTHOG_HOST`
   - `VITE_SENTRY_DSN`
   - `VITE_SENTRY_ENVIRONMENT=production`
   - `VITE_SENTRY_RELEASE` to the deployed release identifier.

## Manual Services

- Supabase Auth: backend `SUPABASE_URL` for JWKS-based JWT verification; frontend `VITE_SUPABASE_URL` and `VITE_SUPABASE_ANON_KEY` for email/password sign-in.
- Paddle billing: `PADDLE_API_KEY`, `PADDLE_WEBHOOK_SECRET`, `PADDLE_ENV`, and price IDs.
- Optional AI: OpenAI or Ollama provider settings.
- Optional backend PostHog analytics: `TELEMETRY_ENABLED=true`, `POSTHOG_API_KEY`, `POSTHOG_HOST`, and `APP_RELEASE`.
- Optional backend Sentry: `SENTRY_DSN`, `SENTRY_ENVIRONMENT=production`, and `SENTRY_RELEASE`.

## Production Guardrails

- The backend refuses to start in production if `DEV_AUTH_BYPASS=true`, `SUPABASE_URL` is missing or invalid, `FRONTEND_ORIGIN` is not an HTTPS origin, or `ALLOWED_HOSTS=*`.
- The frontend build/runtime configuration must include `VITE_API_URL`, `VITE_SUPABASE_URL`, and `VITE_SUPABASE_ANON_KEY` in production.
- Do not configure service-role keys in frontend variables.
- Telemetry must remain disabled locally unless explicitly testing it. Do not put PostHog secret API keys, Sentry auth tokens, Supabase service-role keys, or database credentials in frontend variables.

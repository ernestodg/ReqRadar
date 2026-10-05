# Deployment

## Backend on Railway

1. Create a PostgreSQL database.
2. Set `DATABASE_URL`.
3. Set `APP_ENV=production`.
4. Set `DEV_AUTH_BYPASS=false`.
5. Configure Supabase JWT validation variables before allowing real users.
6. Deploy `backend/Dockerfile`.
7. Run `alembic upgrade head` during container startup.

## Frontend on Cloudflare Pages

1. Set project root to `frontend`.
2. Build command: `npm ci && npm run build`.
3. Output directory: `dist`.
4. Set `VITE_API_URL` to the deployed API origin.

## Manual Services

- Supabase Auth: `SUPABASE_URL`, `SUPABASE_ANON_KEY`, and JWT validation configuration.
- Paddle billing: `PADDLE_API_KEY`, `PADDLE_WEBHOOK_SECRET`, `PADDLE_ENV`, and price IDs.
- Optional AI: OpenAI or Ollama provider settings.
- Optional Sentry: `SENTRY_DSN`.

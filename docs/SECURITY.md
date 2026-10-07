# Security

Controls included in the MVP:

- Dev auth bypass is forbidden in production.
- Production Supabase access tokens are verified against the configured project's JWKS endpoint with issuer, audience, expiration, signature, and subject validation.
- Customer data is scoped by workspace through backend checks.
- Uploaded files are limited to CSV and 10 MB.
- Import retries reject duplicate source CSV uploads for a project, and comparison retries return the existing comparison for the same import pair.
- SQL access uses SQLAlchemy ORM parameterization.
- CSV export escapes formula-leading values.
- Optional integrations are disabled without credentials.
- Product analytics and error monitoring are explicit opt-in. Telemetry payloads exclude uploaded CSV text, requirement content, reviewer notes, authorization headers, cookies, tokens, and request bodies.
- PostHog autocapture and session replay are disabled; ReqRadar emits a small explicit beta-funnel event set only.
- Sentry is configured with default PII disabled and request bodies filtered.
- Responses include request IDs.
- Basic secure headers are added by middleware, including request ID, content-type, frame, referrer, and frame-ancestor protections.

Do not commit `.env` or service credentials.

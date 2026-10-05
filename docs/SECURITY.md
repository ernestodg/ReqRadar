# Security

Controls included in the MVP:

- Dev auth bypass is forbidden in production.
- Production Supabase access tokens are verified against the configured project's JWKS endpoint with issuer, audience, expiration, signature, and subject validation.
- Customer data is scoped by workspace through backend checks.
- Uploaded files are limited to CSV and 10 MB.
- SQL access uses SQLAlchemy ORM parameterization.
- CSV export escapes formula-leading values.
- Optional integrations are disabled without credentials.
- Responses include request IDs.
- Basic secure headers are added by middleware.

Do not commit `.env` or service credentials.

# Phase 4 Telemetry Setup

ReqRadar Phase 4 uses explicit, privacy-bounded telemetry for private beta observation.

## Event Ownership

Backend emits successful persisted business events:

- `project_created`: `workspace_id`, `project_id`
- `import_completed`: `workspace_id`, `project_id`, `import_id`, `version_label`, `requirement_count`, `project_import_count`
- `comparison_completed`: `workspace_id`, `project_id`, `comparison_id`, `modified_count`, `added_count`, `removed_count`, `unchanged_count`, `impact_count`, `high_count`, `medium_count`, `low_count`
- `finding_reviewed`: `workspace_id`, `project_id`, `comparison_id`, `finding_id`, `review_action`, `effective_severity`
- `executive_report_exported`: `workspace_id`, `project_id`, `comparison_id`, `report_type`
- `full_audit_exported`: `workspace_id`, `project_id`, `comparison_id`, `report_type`
- `feedback_submitted`: `workspace_id`, `feedback_type`, `screen`

Frontend emits only:

- `account_created`: `user_id`

All events also include `environment` and `release` when configured.

## Privacy Controls

Never send customer requirement content, uploaded CSV text, filenames, reviewer notes, report/PDF contents, JWTs, authorization headers, cookies, database URLs, API secrets, or passwords.

PostHog frontend settings:

- autocapture disabled
- pageview/pageleave capture disabled
- session recording disabled
- explicit event capture only

Sentry settings:

- default PII disabled
- request bodies disabled on the backend
- event sanitizers filter headers, bodies, cookies, tokens, secrets, and credential-like keys

## Railway Backend Variables

- `TELEMETRY_ENABLED=true`
- `POSTHOG_API_KEY`
- `POSTHOG_HOST`
- `APP_RELEASE`
- `SENTRY_DSN`
- `SENTRY_ENVIRONMENT=production`
- `SENTRY_RELEASE`

Do not set production credentials in the repository.

## Cloudflare Pages Variables

- `VITE_TELEMETRY_ENABLED=true`
- `VITE_POSTHOG_KEY`
- `VITE_POSTHOG_HOST`
- `VITE_SENTRY_DSN`
- `VITE_SENTRY_ENVIRONMENT=production`
- `VITE_SENTRY_RELEASE`

Only browser-safe project keys belong in `VITE_*` variables.

## Manual PostHog Setup

1. Create a PostHog project for ReqRadar beta.
2. Copy the frontend project key into Cloudflare as `VITE_POSTHOG_KEY`.
3. If backend capture is enabled, create/copy the appropriate project API key into Railway as `POSTHOG_API_KEY`.
4. Confirm autocapture and session replay are not used for ReqRadar instrumentation.
5. Verify the activation funnel from explicit events:
   `account_created -> project_created -> import_completed -> import_completed -> comparison_completed -> finding_reviewed -> report exported`.

## Manual Sentry Setup

1. Create Sentry projects for frontend and backend, or one project with clear platform/environment tags.
2. Put frontend DSN in Cloudflare as `VITE_SENTRY_DSN`.
3. Put backend DSN in Railway as `SENTRY_DSN`.
4. Set production environment and release variables on both hosts.
5. Verify Sentry events do not include request bodies, authorization headers, cookies, tokens, uploaded content, or reviewer notes.

## Feedback Retrieval

Beta feedback is stored in the application PostgreSQL `feedback` table:

- `workspace_id`
- `user_id`
- `feedback_type`
- `message`
- `screen`
- `created_at`

Retrieve it with read-only SQL access during beta operations. The free-text message is not sent to PostHog.

## Production Acceptance Checklist

1. Login works normally.
2. Project creation emits `project_created`.
3. First import emits `import_completed`.
4. Second import emits another `import_completed`.
5. Comparison emits `comparison_completed`.
6. Reviewing a finding emits `finding_reviewed`.
7. Executive export emits `executive_report_exported`.
8. Full Audit export emits `full_audit_exported`.
9. Feedback submission persists and emits `feedback_submitted`.
10. Events contain no requirement/customer text.
11. A deliberately triggered safe frontend error appears in Sentry.
12. A deliberately triggered safe backend error appears in Sentry.
13. Sentry events contain no tokens/customer payloads.
14. Disabling or blocking telemetry does not break ReqRadar.

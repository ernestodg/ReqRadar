# Production Smoke Test

Run this after a production deployment or staging release candidate. Use a dedicated non-customer test account and remove test projects afterward.

## Backend

1. Open `/health` on the deployed API.
2. Confirm the response is `{"status":"ok"}`.
3. Confirm response headers include `x-request-id`, `x-content-type-options`, `x-frame-options`, `referrer-policy`, and `content-security-policy`.
4. Verify unauthenticated `/me` returns `401`.
5. Verify authenticated `/me` returns the signed-in user's workspace context.

## Frontend Auth

1. Open the deployed frontend in a private browser session.
2. Confirm the login/create-account screen appears before app data loads.
3. Sign in with the test Supabase account.
4. Confirm the app loads and the header shows the signed-in email.
5. Sign out and confirm the auth screen returns.

## ReqRadar Workflow

1. Create a test project.
2. Import `sample-data/requirements-v1.csv` as `V1`.
3. Import `sample-data/requirements-v2.csv` as `V2`.
4. Compare versions.
5. Confirm the comparison metrics match the expected sample fixture: 16 modified, 2 added, 0 removed, 20 unchanged, 62 findings, 30 high, 32 medium, 0 low.
6. Confirm and dismiss at least one finding, save a reviewer note, and refresh the page.
7. Verify the review state persists.
8. Download the CSV export.
9. Download the Executive Report PDF.
10. Download the Full Audit Report PDF.

## Negative Checks

1. Try uploading a non-CSV file and confirm it is rejected.
2. Try uploading an invalid UTF-8 CSV and confirm it is rejected.
3. Repeat the same CSV import and confirm the duplicate is rejected.
4. Open a comparison URL from another test account and confirm it returns not found.

## Cleanup

Delete the smoke-test project data from the production database only if the deletion path is operationally approved. Otherwise, keep a clearly named smoke project for audit history until the normal data retention process removes it.

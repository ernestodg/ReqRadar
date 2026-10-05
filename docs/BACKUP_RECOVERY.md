# Backup and Recovery

ReqRadar stores customer application data in PostgreSQL. Supabase Auth stores user identities and sessions outside the ReqRadar schema.

## Backup Scope

- PostgreSQL database configured by `DATABASE_URL`.
- Supabase Auth project configuration and users, using Supabase's project backup/export tooling.
- Deployed environment variable names and target hosts. Do not export or commit secret values.

Generated exports and uploaded CSV files are not stored as raw durable files by the backend. They can be regenerated from normalized database records after restore.

## PostgreSQL Backup

Use the hosting provider's scheduled backups for production. For a manual logical backup from a trusted admin workstation:

```bash
pg_dump "$DATABASE_URL" --format=custom --file=reqradar-$(date +%Y%m%d).dump
```

Store backups encrypted in a restricted location. Never place dumps in the repository.

## Restore Drill

1. Provision a new empty PostgreSQL database.
2. Restore the dump:

```bash
pg_restore --clean --if-exists --no-owner --dbname "$RESTORE_DATABASE_URL" reqradar-YYYYMMDD.dump
```

3. Point a staging backend at the restored database.
4. Run:

```bash
alembic current
alembic check
pytest
```

5. Sign in through Supabase Auth on the staging frontend.
6. Confirm project list, comparison details, finding review updates, CSV export, Executive PDF export, and Full Audit PDF export.

## Recovery Notes

- Restore Supabase Auth users before testing authenticated access against a restored application database.
- Keep `DEV_AUTH_BYPASS=false` in every production-like recovery environment.
- Verify `SUPABASE_URL`, `FRONTEND_ORIGIN`, and `ALLOWED_HOSTS` match the recovery environment before exposing it.

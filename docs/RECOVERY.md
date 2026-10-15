# Database recovery runbook

Use this guide when a database migration or backup restore fails. The goal is to preserve the last known-good data before attempting anything else.

## First response

1. Stop normal pharmacy operations in the application and close every running Pharma Khaato window on the affected computer.
2. Do **not** delete, rename, edit, or overwrite any `.sqlite` backup while investigating the failure.
3. Keep the current database file, the newest automatic backup, and every `pre_migration_*.sqlite` / `pharmacy_db_backup_*.sqlite` safety copy.
4. Record the exact error message and the backup path shown by the application. On Windows, make sure no second application process is still holding the database or log files open.

Pharma Khaato stores runtime data in the OS-specific application data directory. Backups are under its `backups` subdirectory and logs are under `logs`.

## If a migration fails

Schema migrations run inside an explicit SQLite transaction. A failed migration is rolled back before the application reports the error.

For an existing installation, Pharma Khaato creates and validates a `pre_migration_*.sqlite` recovery point before applying the first pending migration. The failure message and application log identify that recovery file when one was created.

Recovery procedure:

1. Leave the application closed.
2. Copy the reported `pre_migration_*.sqlite` file to another safe location before doing anything destructive.
3. Preserve the current live database as evidence as well; do not immediately replace it.
4. Check `logs/app.log` for the failing migration filename and error.
5. If the application can start safely, use the normal **Backup & Restore** workflow to restore a verified snapshot rather than replacing files by hand.
6. If the application cannot start, keep both the live database and recovery backup and escalate with the diagnostics listed below before performing a manual file replacement.

Do not repeatedly relaunch an installation that fails at the same migration. Repeated retries do not repair a bad migration and can make troubleshooting harder.

## If a restore fails

Before replacing the live database, the restore workflow creates a separate safety backup. If the restore itself or the post-restore integrity check fails, that safety backup is retained and its path is reported when available.

Recovery procedure:

1. Close the application and keep the reported safety backup untouched.
2. Do not retry restore with the same suspect file until the failure is understood.
3. Keep the source backup that was selected for restore as well as the newly created safety backup.
4. Restart only after confirming that the live database is readable, or after restoring a known-good validated backup through the supported workflow.

The application validates candidate backups with SQLite `PRAGMA quick_check` before trusting them. A file that fails this check must not be promoted to the live database.

## Automatic backup retention

Automatic daily backups use the `auto_pharmacy_db_backup_*.sqlite` prefix. The application keeps the newest 14 automatic snapshots by default, with the configured value constrained to 3–90 snapshots.

Retention cleanup applies **only** to automatic backups. Manual backups and pre-migration safety backups are intentionally excluded from automatic deletion.

## Diagnostics to preserve

When asking for support, preserve these items:

- `logs/app.log`
- application version
- operating system and version
- exact migration filename or restore error text
- path/name of the recovery or safety backup
- result of the application's database health/quick-check diagnostic

Do not include passwords or other credentials in a support bundle or message.

## Manual replacement is a last resort

Directly replacing `pharmacy_db.sqlite` should only be done with all Pharma Khaato processes closed and only after making an additional copy of both the current database and the intended replacement. Prefer the application's validated restore path whenever it is available.

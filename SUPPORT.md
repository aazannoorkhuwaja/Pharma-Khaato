# Pharma Khaato Support

## Before requesting support

1. Open **Settings → System & Recovery**.
2. Run **Check System Again**.
3. If the issue remains, choose **Create Support Bundle**.
4. Note what you were doing, the approximate time, and any message shown on screen.

The support bundle is designed to be privacy-conscious: it does **not** include the live pharmacy database, receipts, exports or backups by default. It contains runtime metadata, readiness results and application logs. Logs can still contain usernames, local file paths and diagnostic messages, so review the ZIP before sharing it outside your organization.

## Protect business data

Do not send the pharmacy database, backup files, exported customer ledgers, passwords or receipt archives unless a trusted support technician explicitly needs a specific file and you have approved that transfer.

Never post business data in a public GitHub issue.

## Recovery

Pharma Khaato creates automatic daily integrity-checked backups and also supports manual backups in **Settings → System & Recovery**.

Restoring a backup:

- requires an administrator/manager account;
- validates the selected SQLite backup;
- creates a safety backup of the current database first;
- restores the selected snapshot;
- requires the application to restart before work continues.

If the workstation has suffered disk failure or the operating system cannot start, preserve the `Pharma-Khaato` application-data directory before reinstalling or replacing the machine.

## Hardware issues

For printer, scanner or cash-drawer problems, record the exact hardware model, connection type (USB/network/Bluetooth), operating system and driver version. Hardware acceptance is workstation-specific and cannot be proven by software CI alone.

## Useful product information

The installed version is visible in the sidebar and in **About Pharma Khaato**. Include that version when reporting a problem.

If a deployment partner or internal administrator manages your installation, contact them first. A support email can be configured for deployed builds through `PHARMA_KHAATO_SUPPORT_EMAIL`.

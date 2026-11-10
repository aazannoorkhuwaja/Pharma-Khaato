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

<!-- coderabbit-ai-generated:v1 -->

<!-- coderabbit-ai-generated-section:v1:e236e4f7e1508c70371dd7feb953fd327e44a5917f4f570a349eca7a5ab965f7 -->

## Recovery

Pharma Khaato checks for automatic integrity-checked backups each minute and saves a snapshot at least hourly while open. Use **Settings → System & Recovery** for a manual backup. Check the second-copy warning and verify a restore from a separate protected device.

Restoring a backup:

- requires an administrator/manager account;
- validates the selected SQLite backup;
- preserves the previous database and journals as recovery evidence;
- restores the selected snapshot;
- requires the application to restart before work continues.

After workstation or disk failure, preserve the application-data directory and external backups before reinstalling. Ask the test lead for help if recovery evidence is incomplete.

## Hardware issues

<!-- /coderabbit-ai-generated:v1 -->

For printer, scanner or cash-drawer problems, record the exact hardware model, connection type (USB/network/Bluetooth), operating system and driver version. Hardware acceptance is workstation-specific and cannot be proven by software CI alone.

## Useful product information

The installed version is visible in the sidebar and in **About Pharma Khaato**. Include that version when reporting a problem.

If a deployment partner or internal administrator manages your installation, contact them first. A support email can be configured for deployed builds through `PHARMA_KHAATO_SUPPORT_EMAIL`.

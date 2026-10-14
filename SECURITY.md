# Security Policy

Pharma Khaato stores pharmacy business data locally and handles financial, inventory and customer-credit records. Treat security issues that could expose, alter or destroy those records as high priority.

## Supported product line

Security fixes are applied to the current launch/release line. Before production deployment, use the latest approved release artifact rather than an old development snapshot.

## Reporting a vulnerability

Do **not** open a public issue containing:

- passwords or authentication material;
- customer information;
- pharmacy databases or backups;
- receipt/export data;
- exploitable security details that have not been remediated.

Report privately to the deployment owner/maintainer. Include the Pharma Khaato version, operating system, reproduction steps and impact. A deployment-specific support address may be configured with `PHARMA_KHAATO_SUPPORT_EMAIL`.

## Security model

Current controls include:

- PBKDF2-HMAC-SHA256 password hashing;
- persistent login lockout;
- backend permission checks in addition to navigation visibility;
- local SQLite foreign-key enforcement and transactional financial workflows;
- checkout idempotency for safe retry after uncertain completion;
- audit logging for sensitive business actions;
- integrity-checked backups and a safety backup before restore;
- per-data-directory single-instance protection for the interactive desktop application;
- support bundles that exclude the live database and business exports by default.

## Deployment requirements

The workstation and operating-system user account remain part of the security boundary. Production deployments should:

1. use a supported, patched Windows/Linux workstation;
2. protect the OS account with a strong password/PIN;
3. restrict physical access to the pharmacy counter computer;
4. keep the live SQLite database on the local workstation, not a network share;
5. copy backups to a separate protected device/location on an appropriate schedule;
6. avoid sharing administrator credentials between staff;
7. verify release checksums before installing downloaded artifacts.

## Known architecture boundary

This release is designed for a local/offline workstation. It is not a multi-branch central-server security architecture. Exposing the SQLite file through a shared network drive, cloud-sync folder or ad-hoc remote-access service is unsupported and can undermine both security and data integrity.

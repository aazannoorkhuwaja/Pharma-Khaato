# Contributing to Pharma Khaato

Pharma Khaato handles real shop money and stock. Preserve transactional correctness and recovery before visual changes. Read [AGENTS.md](AGENTS.md) and [Architecture](docs/ARCHITECTURE.md) before changing a business workflow.

- Work from `develop-ui`; keep changes reviewable and do not merge into `main` without owner approval.
- Keep screens behind MVC controllers. Use background workers for network, filesystem and database work that could block the Qt interface.
- Include meaningful regressions for financial, stock, permission or recovery fixes. Explain changes in operator behaviour and migration requirements in the PR.
- Never include live databases, customer records, passwords, shop certificates/private keys or receipts in issues, fixtures, logs or commits.
- Run `python -m pytest -q`, `python scripts/ui_audit.py` and compilation checks. Use the isolated demo scripts for business/GUI checks; never reset a production data directory.
- Windows is the primary delivery target. Follow [Windows delivery](docs/WINDOWS_DELIVERY.md) and [Update publishing](docs/UPDATES.md) before proposing a release. Native installation and real devices require their own evidence.

Report a bug with app version, Windows version, steps, expected result and actual result. Redact personal/customer details from screenshots. For vulnerabilities, follow [SECURITY.md](SECURITY.md).

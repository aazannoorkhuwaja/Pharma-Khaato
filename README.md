# Pharma Khaato

**An offline pharmacy POS for Windows, built for everyday counter work in Pakistan.**

Sell medicines, track batch stock and expiry, manage customer credit, reconcile cash, and recover saved bills without requiring an internet connection.

**Lead developer and primary contributor: Azaan Noor Khuwaja**

**Contributor: Atif Khan** · [Credits](CREDITS.md) · [MIT License](LICENSE)

## Project status

Version **2.4.0** is an engineering preview for supervised pharmacy testing. Source, business-flow and offscreen GUI checks have passed in the Linux development environment. Native Windows installation and real printer/scanner acceptance still need verification before live rollout. See the [validation record](docs/VALIDATION_2_4_0.md) and [shop acceptance checklist](docs/REAL_WORLD_READINESS.md).

Windows is the primary customer platform. Urdu and Sindhi interfaces are planned after pharmacy feedback; the current interface is English.

## For pharmacy operators

The intended customer delivery is a versioned **Windows Setup EXE**, with a desktop shortcut and an installed getting-started guide. Operators do not need Python, Git or terminal commands.

1. Obtain the reviewed Windows installer and its checksum from your supplier or the project's [published releases](https://github.com/aazannoorkhuwaja/Pharma-Khaato/releases). A source ZIP is not the installer; the 2.4.0 Windows build must pass its native checks before distribution.
2. Install and open **Pharma Khaato** using the same Windows account each day.
3. Create the owner account and configure shop details, prices, units, tax settings and backups.
4. Connect the actual scanner and printer, then complete a supervised trial with test records.
5. Verify opening stock and customer/supplier balances before using real transactions.

Start with the [operator quick start](docs/OPERATOR_QUICK_START.md). For installer requirements and testing, read [Windows delivery](docs/WINDOWS_DELIVERY.md).

**Target:** Windows 10 version 1809 or later / Windows 11, on 64-bit Intel/AMD PCs. Windows 7/8, 32-bit Windows and native ARM builds are not supported targets. Linux is a secondary engineering platform.

## Everyday workflows

| Workflow | Capabilities |
| --- | --- |
| Counter sales | Barcode/name search, tablet/strip/box selection, hold/resume, discounts and saved-bill reprints |
| Payments | Cash, Card, Easypaisa, JazzCash and customer credit; digital tenders stay separate from drawer cash |
| Stock | Batch/lot intake, expiry, pack barcodes, supplier invoices, free stock, counted adjustments and blocked batches |
| Customer credit | Name-first accounts, optional phone/CNIC, partial repayments, statements and auditable corrections |
| Supplier accounts | Invoice balances, later payments and supplier return credits |
| Returns | Original-bill lookup, quantity limits, refund tracking and eligible stock restoration |
| Cash shifts | Opening cash, cash-in/out, counted closing cash and a separate shift for each counter |
| Reports | Gross sales, returns, net sales, tender totals, credit collections, low stock and expiry |
| Recovery | Durable pending operations, validated backups/restores and privacy-conscious support bundles |

Cash customers can remain **Walk-in**. Customer details are only needed when the workflow requires an account, such as credit.

## Offline operation and optional updates

A single shop computer can bill without internet. Multiple local counters use an authenticated TLS connection to one main shop computer; they need the local router and main computer running, even without internet.

The live SQLite database remains on the main computer's local disk. **Never place it on a shared network folder.** Independent offline counter sales and internet multi-branch synchronisation are not implemented.

When enabled, background update checks use internet access to look for a newer published Windows release. The notice shows its release notes and offers **Later** or **Open Update Download**. Nothing installs automatically. Check manually or disable automatic checks under **About Pharma Khaato**. These checks do not transmit shop records. See [update behaviour and publishing](docs/UPDATES.md).

## Data and recovery

Windows shop data normally lives in `%LOCALAPPDATA%\Pharma-Khaato`, outside the installation directory. Use the same Windows account to access the same shop. Updates and uninstall are designed to preserve this directory; verified external backups are still essential.

Financial operations use transactional validation and durable request identities so uncertain retries can recover the original result. Historical receipts preserve sale-time values. Periodic backup snapshots, guarded restores and ordered migrations support recovery. These safeguards do not replace physical power-loss testing or an external backup on another device.

See [Security](SECURITY.md), [Support](SUPPORT.md) and [real-world readiness](docs/REAL_WORLD_READINESS.md).

## Development

Use Python 3.12 or a supported newer runtime. On Windows with the Python launcher installed:

```powershell
git clone -b develop-ui https://github.com/aazannoorkhuwaja/Pharma-Khaato.git
cd Pharma-Khaato
py -3.12 scripts/dev_run.py --demo
```

The launcher creates a project `.venv`. Demo records live only in `.demo-data`; demo credentials and the evaluation flow are documented in the [demo guide](docs/DEMO_GUIDE.md). Never run demo/reset operations against a real shop directory.

Install development dependencies and run the source checks:

```powershell
.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
$env:QT_QPA_PLATFORM = 'offscreen'
.venv\Scripts\python.exe -m pytest -q
.venv\Scripts\python.exe scripts/ui_audit.py
.venv\Scripts\python.exe -m compileall -q main.py controllers core models ui scripts
```

Read [Contributing](CONTRIBUTING.md), [Architecture](docs/ARCHITECTURE.md) and [Developer workflow](docs/DEVELOPER_WORKFLOW.md) before changing business logic. Views use MVC controllers; core services own financial, inventory and permission checks.

Development CI covers Windows and Linux. Release automation builds native packages and verifies the Windows installer before uploading review artifacts. Publishing a stable release remains a separate maintainer action. Work is developed on `develop-ui`; changes to `main` require owner approval and passing review gates.

## Documentation

- [Operator quick start](docs/OPERATOR_QUICK_START.md)
- [Windows installation and delivery](docs/WINDOWS_DELIVERY.md)
- [Shop acceptance and current limits](docs/REAL_WORLD_READINESS.md)
- [Validation evidence](docs/VALIDATION_2_4_0.md)
- [Optional updates and release publishing](docs/UPDATES.md)
- [Demo and evaluation](docs/DEMO_GUIDE.md)
- [Database and migrations](docs/DATABASE.md)
- [Architecture](docs/ARCHITECTURE.md)
- [Contributing](CONTRIBUTING.md)
- [Changelog](CHANGELOG.md)

Licensed under the [MIT License](LICENSE). Builder credits are also available inside the application.

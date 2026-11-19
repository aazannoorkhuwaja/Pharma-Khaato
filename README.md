# Pharma Khaato

**Offline-first pharmacy point-of-sale software for Windows and Linux.**

[![CI on main](https://github.com/aazannoorkhuwaja/Pharma-Khaato/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/aazannoorkhuwaja/Pharma-Khaato/actions/workflows/ci.yml) [![Published prerelease](https://img.shields.io/badge/prerelease-2.5.0-blue)](https://github.com/aazannoorkhuwaja/Pharma-Khaato/releases/tag/v2.5.0) [![License MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE)

[**Releases and downloads**](https://github.com/aazannoorkhuwaja/Pharma-Khaato/releases) · [First-use guide](docs/TRY_IT.md) · [Get help](https://github.com/aazannoorkhuwaja/Pharma-Khaato/issues/new/choose)

Make bills, check stock and expiry, record customer dues, and count the cash in your drawer.

Built and led by **Azaan Noor Khuwaja**, with contributions from **Atif Khan**.

**Engineering overview:** A PySide6 desktop interface connects to Qt-independent Python services through controllers. SQLite (WAL) supports transactional checkout, expiry checks and FEFO stock allocation. [Architecture](docs/ARCHITECTURE.md) · [System flow diagram](docs/diagrams/pharma_khaato_system_flows.svg) · [Verification and acceptance](docs/REAL_WORLD_READINESS.md).

**Release readiness:** The application is an engineering build awaiting pharmacy and hardware acceptance; use practice data until those checks are complete.

## Releases and installer packages

**[2.5.0 test release](https://github.com/aazannoorkhuwaja/Pharma-Khaato/releases/tag/v2.5.0)** · [All releases](https://github.com/aazannoorkhuwaja/Pharma-Khaato/releases) · [SHA-256 checksums](https://github.com/aazannoorkhuwaja/Pharma-Khaato/releases/download/v2.5.0/SHA256SUMS)

| System | Package | How to run it |
| --- | --- | --- |
| Windows 10 or 11 (Intel/AMD 64-bit) | [Download Windows Setup](https://github.com/aazannoorkhuwaja/Pharma-Khaato/releases/download/v2.5.0/Pharma-Khaato-2.5.0-Setup-Windows-x64.exe) | Open the installer, then launch Pharma Khaato from the Start menu. This test installer is unsigned. |
| Ubuntu or Linux Mint (AMD64) | [Download Debian package](https://github.com/aazannoorkhuwaja/Pharma-Khaato/releases/download/v2.5.0/Pharma-Khaato-2.5.0-linux-amd64.deb) | Open the package in your software installer, then launch Pharma Khaato from the applications menu. |
| Other compatible Linux desktops (x86-64) | [Download Linux archive](https://github.com/aazannoorkhuwaja/Pharma-Khaato/releases/download/v2.5.0/Pharma-Khaato-2.5.0-linux-x86_64.tar.gz) | Extract the archive and follow the included START-HERE guide. |

Use practice data for this release. The installers include the runtime. [Windows getting-started guide](https://github.com/aazannoorkhuwaja/Pharma-Khaato/releases/download/v2.5.0/START-HERE.html) · [Linux getting-started guide](https://github.com/aazannoorkhuwaja/Pharma-Khaato/releases/download/v2.5.0/START-HERE-LINUX.html)

The [2.5.1 release candidate](https://github.com/aazannoorkhuwaja/Pharma-Khaato/pull/22) is under review. Its test builds are available through [GitHub Actions](https://github.com/aazannoorkhuwaja/Pharma-Khaato/actions/workflows/release-build.yml).

## Upgrade from 2.5.0 to the 2.5.1 test candidate

The newest changes are in candidate `42e0aac`. The 2.5.0 update notice opens the release page. For this candidate, sign in to GitHub and download the artifact ZIP for your platform. You can upgrade your existing installation without cloning the repository. [Verified build and artifacts](https://github.com/aazannoorkhuwaja/Pharma-Khaato/actions/runs/44477429890)

Use a practice system. If the existing installation holds shop records, verify a recent backup by restoring it on a separate test machine first. If 2.5.0 reports that backup verification failed, stop before upgrading that shop. Finish any pending checkout, close all counters and exit the app before running the installer.

**Windows 10/11 x64.** Extract the entire [Windows installer ZIP](https://github.com/aazannoorkhuwaja/Pharma-Khaato/actions/runs/44477429890/artifacts/14506972924). In the folder containing Setup and its checksum, run PowerShell:

```powershell
$file = 'Pharma-Khaato-2.5.1-Setup-Windows-x64.exe'
$expected = ((Get-Content "$file.sha256" -Raw).Trim() -split '\s+')[0]
if ((Get-FileHash $file -Algorithm SHA256).Hash -ne $expected) { throw 'Checksum mismatch' }
Start-Process -Wait -FilePath ".\$file"
```

Keep the existing installation location. This test build is unsigned. If Windows or your shop policy requires a trusted signature, use the signed release when available.

**Ubuntu amd64.** Extract the [Linux installers ZIP](https://github.com/aazannoorkhuwaja/Pharma-Khaato/actions/runs/44477429890/artifacts/14506418804). Open a terminal in the folder containing the Debian package and checksum:

```bash
sha256sum -c Pharma-Khaato-2.5.1-linux-amd64.deb.sha256 &&
  sudo apt install ./Pharma-Khaato-2.5.1-linux-amd64.deb
```

Launch from Start on Windows or run `pharma-khaato` on Ubuntu. Under the same operating-system account, open **About Pharma Khaato** and confirm **2.5.1**. Check that your practice shop, recent receipt, stock and customer dues are present, then create and verify a new backup. Future stable updates in the candidate offer **Download Verified Update** followed by **Start Installer**.

## Checkout preview

![New Sale screen on Windows showing the practice checkout](docs/images/windows-practice-checkout.png)

Windows capture from the 2.5.1 candidate series with isolated demo data.

## What can I do?

- **Make a bill:** scan a barcode or search for a medicine.
- **Sell different packs:** choose a tablet, strip, box or sealed pack.
- **Take payment:** cash, card, Easypaisa, JazzCash or customer credit.
- **Record dues:** see what a customer owes and record their payment.
- **Check stock:** add stock, check expiry and record supplier bills.
- **Handle returns:** find the original bill and return the right quantity.
- **Count cash:** enter opening cash and count it again when closing.
- **Keep a backup:** save a copy of shop records on another device.

Cash customers do not need to give their name, phone or CNIC. Leave them as **Walk-in**.

After creating your owner account, **Prepare Your Shop** guides you through suppliers, medicines, opening stock and cash. You can reopen it from the sidebar.

## First test at the pharmacy

Use a spare computer and practice records first. Keep the pharmacy's current billing system running for real customers.

For a quick check, receive 100 practice tablets at Rs. 5 selling price each. With zero tax and discount and an open cash shift, sell three tablets to a walk-in customer and enter Rs. 100 received. The bill should show Rs. 15, change Rs. 85, and remaining stock of 97 tablets.

Follow [this short test](docs/TRY_IT.md). It gives you an example medicine, exact amounts to enter, and the stock and cash totals you should see.

Use Windows 10 version 1809 or later, Windows 11, or Ubuntu 22.04/24.04 and compatible Linux desktops, on a 64-bit Intel/AMD computer. Test your own printer and scanner before real sales. ARM is not supported.

## Configuration and connectivity

**No, for billing on one computer.** More than one counter needs the main shop computer and local router running.

Internet is only used for optional update checks. An update notice shows the fixes and lets you choose **Later** or open the download page. Nothing installs by itself. You can turn checks off in **About Pharma Khaato**.

The interface is currently English. Urdu and Sindhi will be added after pharmacy feedback.

## Need help?

- [Try the app: a short pharmacy test](docs/TRY_IT.md)
- [Daily use: simple steps](docs/OPERATOR_QUICK_START.md)
- [What to check before real sales](docs/REAL_WORLD_READINESS.md)
- [Report a problem](https://github.com/aazannoorkhuwaja/Pharma-Khaato/issues/new/choose)

Tell us what you were trying to do, what happened, and the app version. Do not send passwords or customer records.

## For developers

[Setup and code checks](docs/DEVELOPER_WORKFLOW.md) · [Native builds](docs/DEPLOYMENT.md) · [Prepare a release](docs/RELEASING.md) · [Update publishing](docs/UPDATES.md) · [Architecture](docs/ARCHITECTURE.md) · [Contributing](CONTRIBUTING.md) · [Test record](docs/VALIDATION_2_4_0.md)

[Credits](CREDITS.md) · [MIT License](LICENSE)

For the Windows / Ubuntu pharmacy trial, follow [the shop checklist](docs/SHOP_TRIAL.md).

For the first 2.5.0 test release, use the [test handoff](docs/FIRST_TEST_RELEASE.md) and [release notes](docs/releases/2.5.0.md).


## Contributing

Create a branch for your change, run the tests in a Python virtual environment, and open a pull request describing the workflow you changed and how you verified it. From the repository root with the environment active:

```bash
python -m pip install -r requirements-dev.txt
python -m pytest -q
```

See the [contribution guide](CONTRIBUTING.md) for project conventions.

## License

Pharma Khaato source code is distributed under the [MIT License](LICENSE). Bundled third-party components retain their own licenses.

# Pharma Khaato

**A pharmacy billing app for Windows and Linux. It works without internet.**

[**Download**](https://github.com/aazannoorkhuwaja/Pharma-Khaato/releases/latest) · [First-use guide](docs/TRY_IT.md) · [Get help](https://github.com/aazannoorkhuwaja/Pharma-Khaato/issues/new/choose)

Make bills, check stock and expiry, record customer dues, and count the cash in your drawer.

Built and led by **Azaan Noor Khuwaja**, with contributions from **Atif Khan**.

## Install the app

Open the [release downloads](https://github.com/aazannoorkhuwaja/Pharma-Khaato/releases). Choose the file for your computer:

| Computer | File to download | What to do |
| --- | --- | --- |
| Windows 10 or 11, 64-bit Intel/AMD | Ends in **Setup-Windows-x64.exe** | Double-click it, finish Setup, then open Pharma Khaato from your desktop. |
| Ubuntu or Linux Mint, 64-bit Intel/AMD | Ends in **linux-amd64.deb** | Open it with your software installer, install, then open Pharma Khaato from the applications menu. |
| Other compatible Linux desktops | Ends in **linux-x86_64.tar.gz** | Extract it and follow **START-HERE.html** inside. |

**Python and Git are not needed.** Use the app download, not GitHub's “Source code” ZIP.

If no stable release is listed yet, it is still being prepared. The owner can get a test build from [Build Windows and Linux installers](https://github.com/aazannoorkhuwaja/Pharma-Khaato/actions/workflows/release-build.yml): choose **Run workflow**, select **main**, and wait for every job to pass. Download **Windows-installer** or **Linux-installers** under **Artifacts**. Extract that ZIP, then use the Setup or Linux package inside. These test downloads last 30 days and do not publish a release.

Your friend only needs the installer and its **START-HERE** guide. Use practice records until the pharmacy checks below are complete.

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

## First test at the pharmacy

Use a spare computer and practice records first. Keep the pharmacy's current billing system running for real customers.

Follow [this short test](docs/TRY_IT.md). It gives you an example medicine, exact amounts to enter, and the stock and cash totals you should see.

Use Windows 10 version 1809 or later, Windows 11, or Ubuntu 22.04/24.04 and compatible Linux desktops, on a 64-bit Intel/AMD computer. Test your own printer and scanner before real sales. ARM is not supported.

## Does it need internet?

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

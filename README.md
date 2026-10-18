# Pharma Khaato

**A pharmacy billing app for Windows. It works without internet.**

Make bills, check stock and expiry, record customer dues, and count the cash in your drawer.

Built and led by **Azaan Noor Khuwaja**, with contributions from **Atif Khan**.

## How do I try it?

You do not need a public release to get a test installer.

1. Open [Build Windows installer](https://github.com/aazannoorkhuwaja/Pharma-Khaato/actions/workflows/release-build.yml).
2. Click **Run workflow**, choose **main**, then click **Run workflow** again.
3. Wait for the build to finish with a green tick.
4. Open that run. Under **Artifacts**, download **Windows-installer**.
5. Extract the ZIP and double-click the file ending in **Setup-Windows-x64.exe**.
6. Open **Pharma Khaato** from your desktop. The included **START-HERE.html** explains what to do next.

Once these changes reach `main`, a test installer will also be built after each merge. It stays in Actions for 30 days. This does not publish a public release.

The owner downloads the installer and sends it to the tester. Your friend does not need GitHub, Python or any commands to use the app. If a build fails, get it fixed before sharing the installer.

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

Use Windows 10 version 1809 or later, or Windows 11, on a 64-bit Intel/AMD computer. Windows checks passing does not replace testing your own printer and scanner.

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

[Setup and code checks](docs/DEVELOPER_WORKFLOW.md) · [Windows builds](docs/WINDOWS_DELIVERY.md) · [Update publishing](docs/UPDATES.md) · [Architecture](docs/ARCHITECTURE.md) · [Contributing](CONTRIBUTING.md) · [Test record](docs/VALIDATION_2_4_0.md)

[Credits](CREDITS.md) · [MIT License](LICENSE)

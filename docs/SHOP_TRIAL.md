# Try the app at your pharmacy

Use a separate practice shop first. Keep your current billing system available until the owner has checked the results.

## Install or update

- Windows: download the Windows installer, close Pharma Khaato, and run Setup. Open the app from the Start menu.
- Ubuntu / Linux Mint: download and extract Linux-installers, then open the file ending in `.deb` with your software installer.
- If this computer already has shop records, use Settings → System & Recovery → Create Backup Now before updating. Copy a backup to another device.
- Check About Pharma Khaato shows **2.4.2**. Updating preserves existing accounts and records.

For an isolated Ubuntu practice shop, close the app and run:

```bash
PHARMA_KHAATO_DATA_DIR="$HOME/.local/share/pharma-khaato-practice" pharma-khaato
```

Use this command each time you want the practice shop. The normal menu shortcut opens your original shop.

## Prepare the shop

1. Create your owner account and keep the password safe.
2. Open Prepare Your Shop. Add your supplier and medicines, then receive opening stock with the correct quantity, pack size, cost and expiry.
3. Check the pharmacy name, tax setting and receipt details in Settings.
4. Create a separate Cashier account in Staff Access. Sign out and confirm the cashier can sign in. Do not give every staff member the Owner role.
5. Open Printer Setup. Choose your installed printer, set the paper width and print a test. Confirm the amount, medicine name and bottom of the receipt are readable.
6. Start a shift with the actual cash in the drawer.

## Check before using real sales

Follow the worked example in [Try It](TRY_IT.md): receive 100 tablets, sell individual tablets and a strip, return one tablet, and reconcile the remaining stock and cash.

Also check these tasks:

- Make one cash sale and one card or wallet sale. Confirm the wallet payment separately; choosing Easypaisa or Card records the method and does not collect the payment for you.
- If printing fails after a sale, use the saved sale's reprint action. Do not make the sale again.
- Hold and resume a sale. Close and reopen the app and confirm saved bills remain.
- Make a customer credit sale, collect a payment, and check the remaining amount owed.
- Receive a supplier invoice and check both the stock and amount owed to that supplier.
- Count drawer cash and close the shift. Read the difference and closing summary.
- Create a backup and test restoring it on a separate practice computer before relying on it for recovery.
- Check Settings and invoice entry in both themes and at your preferred text size.

A barcode scanner is optional. Search by medicine name now. When a scanner is added, test medicine and pack barcodes and check the selected selling unit before saving a bill.

## Ask for help

Record the app version, the task you tried, and the message shown. Hide customer details in screenshots. Never send passwords or your entire shop database as a routine support attachment.

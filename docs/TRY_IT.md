# Try Pharma Khaato at the pharmacy

Use a spare computer first. Keep using the pharmacy's current system for real customers. These are practice records, not real sales.

## Get the app

Ask the owner for the Windows Setup file. Double-click it, keep the desktop shortcut selected, and finish the setup. Open **Pharma Khaato** from your desktop.

If you are the owner downloading it from GitHub, follow the steps in the [README](../README.md). There is no need to publish a release.

## Set up a practice shop

1. Enter a practice shop name and create your owner account. Keep the password.
2. For this example, keep sales tax at **0%** and do not add a discount.
3. Add a practice supplier.
4. Add **Practice Medicine 500mg**. Set the smallest unit to tablet, the price to **Rs. 5 per tablet**, and **10 tablets per strip**.
5. Add **100 tablets** as stock, with a future expiry date. This is the total quantity, not 100 strips.
6. Start a cash shift with **Rs. 1,000** in opening cash.

## Make two bills and a return

| Do this | What you should see |
| --- | --- |
| Sell 3 tablets for cash. Enter Rs. 100 received. | Bill Rs. 15; change Rs. 85; stock 97 tablets. |
| Start a new bill. Sell 1 strip of 10 tablets. Take exactly Rs. 50 cash. | Bill Rs. 50; stock 87 tablets. |
| Open the first bill and return 1 tablet. Refund Rs. 5 cash. | Stock 88 tablets. |
| Check the cash totals. | Expected drawer cash Rs. 1,060: opening 1,000 + sales 65 − refund 5. |

Do not add a customer for these cash bills. **Walk-in** is enough.

## Try the other everyday tasks

- Make a bill, choose **Hold Sale**, and open it again from **Held Sales**.
- Add a practice customer using only a name. Make a credit sale, then record a payment. Check that the amount owed goes down.
- Print a receipt. If the printer fails, reprint the saved bill rather than making a new sale.
- Disconnect internet and make another practice bill. It should still work on a single computer.
- Close and reopen the app using the same Windows account. Check that saved bills are still there.
- Count the drawer and close the cash shift. Use the updated expected amount if you made extra practice transactions.

Before trying a second counter, ask the person setting up the shop to connect it properly.

## Tell us what was difficult

Ask your friend to do the tasks without coaching. For each problem, write:

- What were you trying to do?
- What did you expect?
- What happened, or which words were confusing?
- What version is shown in About Pharma Khaato?

A screenshot helps, but hide customer details and never share passwords.

Do not delete the shop data folder to remove practice records. Agree on a clean setup with the owner before switching to real sales. Real opening stock, customer dues and supplier balances must be checked first.

## It asks me to sign in before setup

An older installation may already have created an account on this computer. Reinstalling keeps its shop records and password. Use that account; `admin / demo1234` works only in the separately prepared developer demo, not in a normal installation.

On Linux, you can open a separate practice shop without changing the old records. Close the app, then run this command if you installed the Linux package:

```bash
PHARMA_KHAATO_DATA_DIR="$HOME/.local/share/pharma-khaato-practice" pharma-khaato
```

The first time, create your own practice username and password. Use the same command and those credentials to reopen this practice shop. The normal applications-menu shortcut still opens the original shop. This is for testing; keep practice records separate from real sales.

For a staff password, ask the owner to use **Settings → Staff Access**. If the owner cannot sign in, contact support before changing files. Do not delete the data folder or overwrite the old database to get past sign-in.

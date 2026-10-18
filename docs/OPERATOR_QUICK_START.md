# Shop operator quick start

## Owner: prepare the shop once

1. Create your owner account. Give each cashier their own staff account; keep the owner password private.
2. Open **Settings**. Enter the real shop name, address and phone. Review and save the sales tax percentage. `1` means **1%**. Check the rules with your accountant; the application does not determine tax eligibility.
3. Choose and test the receipt printer on each computer. Check the actual 58 mm or 80 mm paper, Urdu names, long medicine names and totals.
4. Choose a backup location on another drive on the main computer. Automatic snapshots also remain on that computer; a second folder on the same disk will not protect against disk failure. Practise restoring a backup on a spare installation before going live.
5. Add suppliers and medicines. Include strength and form in medicine names. Choose the smallest unit you sell: tablet, capsule, bottle, sachet or sealed pack. Set how many base units are in a strip and box. Give each pack barcode its correct unit.
6. Receive real stock with the supplier invoice, batch/lot, expiry and prices. For month-only expiry, enter `MM/YYYY`; the app treats that as the last day of the month. Selling price is per base unit. Invoice buying cost is per selected purchasing unit. Free stock is entered in base units.
7. Count existing stock and correct differences with a reason. Block damaged or questionable batches so they cannot be sold.

## Cashier: start and sell

1. Sign in with your own account and open a cash shift. Enter the cash actually placed in the drawer.
2. Scan a barcode, or search by medicine name/strength. Confirm the medicine and unit. A box and a tablet have different quantities and prices.
3. Use **Walk-in** for ordinary sales. Customer details are unnecessary for a cash sale.
4. For credit (Khaato / Udhaar), select the correct customer account. A name is sufficient to create an account; phone helps distinguish similar names. CNIC is optional. Check the customer before confirming credit.
5. Choose Cash, Card, Easypaisa, JazzCash or Customer Credit. Only mark a digital payment after verifying that you received it. For cash, enter money received or choose exact cash; check the change displayed.
6. Confirm once. If the outcome is uncertain, use the pending-bill status/retry action. Keep the same pending bill until its result is known. Do not create a replacement bill to work around a connection error.
7. If printing fails, the sale can still be saved. Fix the printer and reprint that sale. A reprint does not create another sale.

Use **Hold** before leaving an unfinished cart or changing cashier. An ordinary unsubmitted cart is not a saved bill. Pending submitted bills are preserved for recovery.

## Customer payments and returns

- Select the customer's account, enter the amount actually received and select the correct payment method. Payments settle the oldest outstanding credit first. Check the remaining balance and give the customer their slip.
- If a repayment result is uncertain, confirm the pending payment before entering another one. Owner corrections keep an audit history.
- Find the original bill for a return. Select quantities and refund method, review the summary, then confirm. Never refund more than the actual return. Only eligible stock is put back into saleable inventory.
- For supplier stock, use **Supplier Invoices & Payments**. Record an invoice once, then record later payments against the supplier account. Choose **Cash from drawer** only when taking cash from the active drawer; bank and outside-drawer payments are separate.

## End of shift

Count the cash yourself. Record genuine cash paid in/out with a reason. Enter the counted closing cash and review any difference. Digital payments do not increase drawer cash. Reconcile the card/mobile-wallet records separately. Finish pending operations before signing out or switching computers.

## More than one counter

On the owner computer, use **Shop Computers** and choose the main-computer mode. Keep it on, awake and running while other counters work. Give it a stable local IP address or computer name. Copy only its public shop certificate to each counter; never copy its private key or live database. On each counter choose the main shop address, trusted certificate and a unique counter name. Each drawer has its own cash shift. Internet is unnecessary, but the shop's local network and main computer must be available. Stop new sales on a disconnected counter and resolve pending results when the connection returns.

Backup settings and restores belong on the main computer. Restore requires all counters to stop work and restart afterwards. A technician must check the firewall, address/certificate and recovery procedure during initial setup. Do not share the live SQLite file through a network folder.

## Before serving real customers

Perform the checks in [REAL_WORLD_READINESS.md](REAL_WORLD_READINESS.md) with the actual shop staff, computer, scanner and printer. Medicine selection, prescription checking and dispensing remain the responsibility of qualified pharmacy staff.

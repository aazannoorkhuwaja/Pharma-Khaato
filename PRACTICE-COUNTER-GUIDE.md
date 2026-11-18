# Pharmacy counter practice

Run `python3 run_practice.py` from this folder on Ubuntu or `py -3.12 run_practice.py` on Windows with the project dependencies installed. Add `--new` for a separate practice shop. Use invented customer and medicine records.

1. Complete owner setup. Enter only a discount rate approved for the shop. Zero disables the government discount. On the sign-in screen enter the administrator username, select **Owner recovery code**, and create a code using the current password. Store the code offline. Generating another code replaces the previous one.
2. Sign in and open a cash shift with the counted drawer amount. Add a supplier, select an existing medicine in Inventory and choose **Receive More Stock**. Enter the printed lot, expiry, supplier invoice, unit and quantity. Receive a second lot with a different expiry and check the expiring units and printed lot in Alerts.
3. On New Sale, scan or search for a medicine. Select the customer or use Add Customer. Review the government discount, then verify the owner's configured customer discount. This practice implementation applies the owner percentage to the price after the government discount. Additional rupee discount comes off before tax. Check a worked receipt with the owner.
4. For a final bill of Rs. 6,000 choose Cash, clear Exact Cash, enter Rs. 4,000 and confirm Rs. 2,000 to Khatoo. Verify the receipt, the customer statement and the physical drawer. Collect later repayments through Khatoo.
5. In Returns select **Find my last sale** during the same sign-in, or enter the sale number printed on the receipt. A Rs. 2,500 eligible return on the example invoice first clears Rs. 2,000 due and refunds Rs. 500 cash if there were no later collections. Confirm returned goods disposition before proceeding.
6. Count the drawer, review the cash shift variance, close the shift and verify a backup. Sign out before handing the counter to another employee.

For an unassisted pilot, record expected and actual results for ten bills covering exact cash, change, a government discount, an owner discount, both discounts together, credit, partial cash, later collection, a return and a receipt reprint. Record the installer revision, Windows display scale, printer and scanner models. Keep practice evidence free of customer identifiers.

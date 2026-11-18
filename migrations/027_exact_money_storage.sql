-- Exact integer ledger storage; preserve old monetary API columns as projections.
-- Conversion is deterministic Decimal ROUND_HALF_UP via the application connection.

CREATE TABLE Money_Migration_Evidence (
 table_name TEXT NOT NULL, column_name TEXT NOT NULL, row_count INTEGER NOT NULL,
 scale INTEGER NOT NULL, total_minor INTEGER NOT NULL, rounded_rows INTEGER NOT NULL,
 PRIMARY KEY(table_name,column_name)
);

ALTER TABLE "Products" ADD COLUMN "price_minor" INTEGER CHECK("price_minor" IS NULL OR typeof("price_minor")='integer');

UPDATE "Products" SET "price_minor"=money_to_units("price",10000);

INSERT INTO Money_Migration_Evidence SELECT 'Products','price',COUNT(*),10000,COALESCE(SUM("price_minor"),0),COALESCE(SUM(CASE WHEN "price" != "price_minor"/10000.0 THEN 1 ELSE 0 END),0) FROM "Products";

UPDATE "Products" SET "price"="price_minor"/10000.0;

CREATE TRIGGER money_Products_insert AFTER INSERT ON "Products"
BEGIN UPDATE "Products" SET "price_minor"=money_to_units(NEW."price",10000),"price"=money_to_units(NEW."price",10000)/10000.0 WHERE rowid=NEW.rowid; END;

CREATE TRIGGER money_Products_update AFTER UPDATE OF "price" ON "Products"
BEGIN UPDATE "Products" SET "price_minor"=money_to_units(NEW."price",10000),"price"=money_to_units(NEW."price",10000)/10000.0 WHERE rowid=NEW.rowid; END;

CREATE TRIGGER money_Products_guard BEFORE UPDATE OF "price_minor" ON "Products"
WHEN NEW."price_minor" IS NOT money_to_units(NEW."price",10000)
BEGIN SELECT RAISE(ABORT,'Integer money and compatibility values must agree'); END;

ALTER TABLE "Batch" ADD COLUMN "cost_price_minor" INTEGER CHECK("cost_price_minor" IS NULL OR typeof("cost_price_minor")='integer');

UPDATE "Batch" SET "cost_price_minor"=money_to_units("cost_price",10000);

INSERT INTO Money_Migration_Evidence SELECT 'Batch','cost_price',COUNT(*),10000,COALESCE(SUM("cost_price_minor"),0),COALESCE(SUM(CASE WHEN "cost_price" != "cost_price_minor"/10000.0 THEN 1 ELSE 0 END),0) FROM "Batch";

UPDATE "Batch" SET "cost_price"="cost_price_minor"/10000.0;

ALTER TABLE "Batch" ADD COLUMN "sale_price_minor" INTEGER CHECK("sale_price_minor" IS NULL OR typeof("sale_price_minor")='integer');

UPDATE "Batch" SET "sale_price_minor"=money_to_units("sale_price",10000);

INSERT INTO Money_Migration_Evidence SELECT 'Batch','sale_price',COUNT(*),10000,COALESCE(SUM("sale_price_minor"),0),COALESCE(SUM(CASE WHEN "sale_price" != "sale_price_minor"/10000.0 THEN 1 ELSE 0 END),0) FROM "Batch";

UPDATE "Batch" SET "sale_price"="sale_price_minor"/10000.0;

ALTER TABLE "Batch" ADD COLUMN "mrp_minor" INTEGER CHECK("mrp_minor" IS NULL OR typeof("mrp_minor")='integer');

UPDATE "Batch" SET "mrp_minor"=money_to_units("mrp",10000);

INSERT INTO Money_Migration_Evidence SELECT 'Batch','mrp',COUNT(*),10000,COALESCE(SUM("mrp_minor"),0),COALESCE(SUM(CASE WHEN "mrp" != "mrp_minor"/10000.0 THEN 1 ELSE 0 END),0) FROM "Batch";

UPDATE "Batch" SET "mrp"="mrp_minor"/10000.0;

CREATE TRIGGER money_Batch_insert AFTER INSERT ON "Batch"
BEGIN UPDATE "Batch" SET "cost_price_minor"=money_to_units(NEW."cost_price",10000),"cost_price"=money_to_units(NEW."cost_price",10000)/10000.0,"sale_price_minor"=money_to_units(NEW."sale_price",10000),"sale_price"=money_to_units(NEW."sale_price",10000)/10000.0,"mrp_minor"=money_to_units(NEW."mrp",10000),"mrp"=money_to_units(NEW."mrp",10000)/10000.0 WHERE rowid=NEW.rowid; END;

CREATE TRIGGER money_Batch_update AFTER UPDATE OF "cost_price","sale_price","mrp" ON "Batch"
BEGIN UPDATE "Batch" SET "cost_price_minor"=money_to_units(NEW."cost_price",10000),"cost_price"=money_to_units(NEW."cost_price",10000)/10000.0,"sale_price_minor"=money_to_units(NEW."sale_price",10000),"sale_price"=money_to_units(NEW."sale_price",10000)/10000.0,"mrp_minor"=money_to_units(NEW."mrp",10000),"mrp"=money_to_units(NEW."mrp",10000)/10000.0 WHERE rowid=NEW.rowid; END;

CREATE TRIGGER money_Batch_guard BEFORE UPDATE OF "cost_price_minor","sale_price_minor","mrp_minor" ON "Batch"
WHEN NEW."cost_price_minor" IS NOT money_to_units(NEW."cost_price",10000) OR NEW."sale_price_minor" IS NOT money_to_units(NEW."sale_price",10000) OR NEW."mrp_minor" IS NOT money_to_units(NEW."mrp",10000)
BEGIN SELECT RAISE(ABORT,'Integer money and compatibility values must agree'); END;

ALTER TABLE "Purchase" ADD COLUMN "total_price_minor" INTEGER CHECK("total_price_minor" IS NULL OR typeof("total_price_minor")='integer');

UPDATE "Purchase" SET "total_price_minor"=money_to_units("total_price",100);

INSERT INTO Money_Migration_Evidence SELECT 'Purchase','total_price',COUNT(*),100,COALESCE(SUM("total_price_minor"),0),COALESCE(SUM(CASE WHEN "total_price" != "total_price_minor"/100.0 THEN 1 ELSE 0 END),0) FROM "Purchase";

UPDATE "Purchase" SET "total_price"="total_price_minor"/100.0;

ALTER TABLE "Purchase" ADD COLUMN "price_with_tax_minor" INTEGER CHECK("price_with_tax_minor" IS NULL OR typeof("price_with_tax_minor")='integer');

UPDATE "Purchase" SET "price_with_tax_minor"=money_to_units("price_with_tax",100);

INSERT INTO Money_Migration_Evidence SELECT 'Purchase','price_with_tax',COUNT(*),100,COALESCE(SUM("price_with_tax_minor"),0),COALESCE(SUM(CASE WHEN "price_with_tax" != "price_with_tax_minor"/100.0 THEN 1 ELSE 0 END),0) FROM "Purchase";

UPDATE "Purchase" SET "price_with_tax"="price_with_tax_minor"/100.0;

ALTER TABLE "Purchase" ADD COLUMN "discount_amount_minor" INTEGER CHECK("discount_amount_minor" IS NULL OR typeof("discount_amount_minor")='integer');

UPDATE "Purchase" SET "discount_amount_minor"=money_to_units("discount_amount",100);

INSERT INTO Money_Migration_Evidence SELECT 'Purchase','discount_amount',COUNT(*),100,COALESCE(SUM("discount_amount_minor"),0),COALESCE(SUM(CASE WHEN "discount_amount" != "discount_amount_minor"/100.0 THEN 1 ELSE 0 END),0) FROM "Purchase";

UPDATE "Purchase" SET "discount_amount"="discount_amount_minor"/100.0;

ALTER TABLE "Purchase" ADD COLUMN "cash_received_minor" INTEGER CHECK("cash_received_minor" IS NULL OR typeof("cash_received_minor")='integer');

UPDATE "Purchase" SET "cash_received_minor"=money_to_units("cash_received",100);

INSERT INTO Money_Migration_Evidence SELECT 'Purchase','cash_received',COUNT(*),100,COALESCE(SUM("cash_received_minor"),0),COALESCE(SUM(CASE WHEN "cash_received" != "cash_received_minor"/100.0 THEN 1 ELSE 0 END),0) FROM "Purchase";

UPDATE "Purchase" SET "cash_received"="cash_received_minor"/100.0;

ALTER TABLE "Purchase" ADD COLUMN "change_due_minor" INTEGER CHECK("change_due_minor" IS NULL OR typeof("change_due_minor")='integer');

UPDATE "Purchase" SET "change_due_minor"=money_to_units("change_due",100);

INSERT INTO Money_Migration_Evidence SELECT 'Purchase','change_due',COUNT(*),100,COALESCE(SUM("change_due_minor"),0),COALESCE(SUM(CASE WHEN "change_due" != "change_due_minor"/100.0 THEN 1 ELSE 0 END),0) FROM "Purchase";

UPDATE "Purchase" SET "change_due"="change_due_minor"/100.0;

ALTER TABLE "Purchase" ADD COLUMN "total_tax_minor" INTEGER CHECK("total_tax_minor" IS NULL OR typeof("total_tax_minor")='integer');

UPDATE "Purchase" SET "total_tax_minor"=money_to_units("total_tax",100);

INSERT INTO Money_Migration_Evidence SELECT 'Purchase','total_tax',COUNT(*),100,COALESCE(SUM("total_tax_minor"),0),COALESCE(SUM(CASE WHEN "total_tax" != "total_tax_minor"/100.0 THEN 1 ELSE 0 END),0) FROM "Purchase";

UPDATE "Purchase" SET "total_tax"="total_tax_minor"/100.0;

CREATE TRIGGER money_Purchase_insert AFTER INSERT ON "Purchase"
BEGIN UPDATE "Purchase" SET "total_price_minor"=money_to_units(NEW."total_price",100),"total_price"=money_to_units(NEW."total_price",100)/100.0,"price_with_tax_minor"=money_to_units(NEW."price_with_tax",100),"price_with_tax"=money_to_units(NEW."price_with_tax",100)/100.0,"discount_amount_minor"=money_to_units(NEW."discount_amount",100),"discount_amount"=money_to_units(NEW."discount_amount",100)/100.0,"cash_received_minor"=money_to_units(NEW."cash_received",100),"cash_received"=money_to_units(NEW."cash_received",100)/100.0,"change_due_minor"=money_to_units(NEW."change_due",100),"change_due"=money_to_units(NEW."change_due",100)/100.0,"total_tax_minor"=money_to_units(NEW."total_tax",100),"total_tax"=money_to_units(NEW."total_tax",100)/100.0 WHERE rowid=NEW.rowid; END;

CREATE TRIGGER money_Purchase_update AFTER UPDATE OF "total_price","price_with_tax","discount_amount","cash_received","change_due","total_tax" ON "Purchase"
BEGIN UPDATE "Purchase" SET "total_price_minor"=money_to_units(NEW."total_price",100),"total_price"=money_to_units(NEW."total_price",100)/100.0,"price_with_tax_minor"=money_to_units(NEW."price_with_tax",100),"price_with_tax"=money_to_units(NEW."price_with_tax",100)/100.0,"discount_amount_minor"=money_to_units(NEW."discount_amount",100),"discount_amount"=money_to_units(NEW."discount_amount",100)/100.0,"cash_received_minor"=money_to_units(NEW."cash_received",100),"cash_received"=money_to_units(NEW."cash_received",100)/100.0,"change_due_minor"=money_to_units(NEW."change_due",100),"change_due"=money_to_units(NEW."change_due",100)/100.0,"total_tax_minor"=money_to_units(NEW."total_tax",100),"total_tax"=money_to_units(NEW."total_tax",100)/100.0 WHERE rowid=NEW.rowid; END;

CREATE TRIGGER money_Purchase_guard BEFORE UPDATE OF "total_price_minor","price_with_tax_minor","discount_amount_minor","cash_received_minor","change_due_minor","total_tax_minor" ON "Purchase"
WHEN NEW."total_price_minor" IS NOT money_to_units(NEW."total_price",100) OR NEW."price_with_tax_minor" IS NOT money_to_units(NEW."price_with_tax",100) OR NEW."discount_amount_minor" IS NOT money_to_units(NEW."discount_amount",100) OR NEW."cash_received_minor" IS NOT money_to_units(NEW."cash_received",100) OR NEW."change_due_minor" IS NOT money_to_units(NEW."change_due",100) OR NEW."total_tax_minor" IS NOT money_to_units(NEW."total_tax",100)
BEGIN SELECT RAISE(ABORT,'Integer money and compatibility values must agree'); END;

ALTER TABLE "Sales_details" ADD COLUMN "unit_price_minor" INTEGER CHECK("unit_price_minor" IS NULL OR typeof("unit_price_minor")='integer');

UPDATE "Sales_details" SET "unit_price_minor"=money_to_units("unit_price",100000000);

INSERT INTO Money_Migration_Evidence SELECT 'Sales_details','unit_price',COUNT(*),100000000,COALESCE(SUM("unit_price_minor"),0),COALESCE(SUM(CASE WHEN "unit_price" != "unit_price_minor"/100000000.0 THEN 1 ELSE 0 END),0) FROM "Sales_details";

UPDATE "Sales_details" SET "unit_price"="unit_price_minor"/100000000.0;

ALTER TABLE "Sales_details" ADD COLUMN "line_subtotal_minor" INTEGER CHECK("line_subtotal_minor" IS NULL OR typeof("line_subtotal_minor")='integer');

UPDATE "Sales_details" SET "line_subtotal_minor"=money_to_units("line_subtotal",100);

INSERT INTO Money_Migration_Evidence SELECT 'Sales_details','line_subtotal',COUNT(*),100,COALESCE(SUM("line_subtotal_minor"),0),COALESCE(SUM(CASE WHEN "line_subtotal" != "line_subtotal_minor"/100.0 THEN 1 ELSE 0 END),0) FROM "Sales_details";

UPDATE "Sales_details" SET "line_subtotal"="line_subtotal_minor"/100.0;

CREATE TRIGGER money_Sales_details_insert AFTER INSERT ON "Sales_details"
BEGIN UPDATE "Sales_details" SET "unit_price_minor"=money_to_units(NEW."unit_price",100000000),"unit_price"=money_to_units(NEW."unit_price",100000000)/100000000.0,"line_subtotal_minor"=money_to_units(NEW."line_subtotal",100),"line_subtotal"=money_to_units(NEW."line_subtotal",100)/100.0 WHERE rowid=NEW.rowid; END;

CREATE TRIGGER money_Sales_details_update AFTER UPDATE OF "unit_price","line_subtotal" ON "Sales_details"
BEGIN UPDATE "Sales_details" SET "unit_price_minor"=money_to_units(NEW."unit_price",100000000),"unit_price"=money_to_units(NEW."unit_price",100000000)/100000000.0,"line_subtotal_minor"=money_to_units(NEW."line_subtotal",100),"line_subtotal"=money_to_units(NEW."line_subtotal",100)/100.0 WHERE rowid=NEW.rowid; END;

CREATE TRIGGER money_Sales_details_guard BEFORE UPDATE OF "unit_price_minor","line_subtotal_minor" ON "Sales_details"
WHEN NEW."unit_price_minor" IS NOT money_to_units(NEW."unit_price",100000000) OR NEW."line_subtotal_minor" IS NOT money_to_units(NEW."line_subtotal",100)
BEGIN SELECT RAISE(ABORT,'Integer money and compatibility values must agree'); END;

ALTER TABLE "Customer_Khatoo" ADD COLUMN "amount_paid_minor" INTEGER CHECK("amount_paid_minor" IS NULL OR typeof("amount_paid_minor")='integer');

UPDATE "Customer_Khatoo" SET "amount_paid_minor"=money_to_units("amount_paid",100);

INSERT INTO Money_Migration_Evidence SELECT 'Customer_Khatoo','amount_paid',COUNT(*),100,COALESCE(SUM("amount_paid_minor"),0),COALESCE(SUM(CASE WHEN "amount_paid" != "amount_paid_minor"/100.0 THEN 1 ELSE 0 END),0) FROM "Customer_Khatoo";

UPDATE "Customer_Khatoo" SET "amount_paid"="amount_paid_minor"/100.0;

ALTER TABLE "Customer_Khatoo" ADD COLUMN "amount_due_minor" INTEGER CHECK("amount_due_minor" IS NULL OR typeof("amount_due_minor")='integer');

UPDATE "Customer_Khatoo" SET "amount_due_minor"=money_to_units("amount_due",100);

INSERT INTO Money_Migration_Evidence SELECT 'Customer_Khatoo','amount_due',COUNT(*),100,COALESCE(SUM("amount_due_minor"),0),COALESCE(SUM(CASE WHEN "amount_due" != "amount_due_minor"/100.0 THEN 1 ELSE 0 END),0) FROM "Customer_Khatoo";

UPDATE "Customer_Khatoo" SET "amount_due"="amount_due_minor"/100.0;

CREATE TRIGGER money_Customer_Khatoo_insert AFTER INSERT ON "Customer_Khatoo"
BEGIN UPDATE "Customer_Khatoo" SET "amount_paid_minor"=money_to_units(NEW."amount_paid",100),"amount_paid"=money_to_units(NEW."amount_paid",100)/100.0,"amount_due_minor"=money_to_units(NEW."amount_due",100),"amount_due"=money_to_units(NEW."amount_due",100)/100.0 WHERE rowid=NEW.rowid; END;

CREATE TRIGGER money_Customer_Khatoo_update AFTER UPDATE OF "amount_paid","amount_due" ON "Customer_Khatoo"
BEGIN UPDATE "Customer_Khatoo" SET "amount_paid_minor"=money_to_units(NEW."amount_paid",100),"amount_paid"=money_to_units(NEW."amount_paid",100)/100.0,"amount_due_minor"=money_to_units(NEW."amount_due",100),"amount_due"=money_to_units(NEW."amount_due",100)/100.0 WHERE rowid=NEW.rowid; END;

CREATE TRIGGER money_Customer_Khatoo_guard BEFORE UPDATE OF "amount_paid_minor","amount_due_minor" ON "Customer_Khatoo"
WHEN NEW."amount_paid_minor" IS NOT money_to_units(NEW."amount_paid",100) OR NEW."amount_due_minor" IS NOT money_to_units(NEW."amount_due",100)
BEGIN SELECT RAISE(ABORT,'Integer money and compatibility values must agree'); END;

ALTER TABLE "Cash_Register_Session" ADD COLUMN "opening_cash_minor" INTEGER CHECK("opening_cash_minor" IS NULL OR typeof("opening_cash_minor")='integer');

UPDATE "Cash_Register_Session" SET "opening_cash_minor"=money_to_units("opening_cash",100);

INSERT INTO Money_Migration_Evidence SELECT 'Cash_Register_Session','opening_cash',COUNT(*),100,COALESCE(SUM("opening_cash_minor"),0),COALESCE(SUM(CASE WHEN "opening_cash" != "opening_cash_minor"/100.0 THEN 1 ELSE 0 END),0) FROM "Cash_Register_Session";

UPDATE "Cash_Register_Session" SET "opening_cash"="opening_cash_minor"/100.0;

ALTER TABLE "Cash_Register_Session" ADD COLUMN "closing_cash_actual_minor" INTEGER CHECK("closing_cash_actual_minor" IS NULL OR typeof("closing_cash_actual_minor")='integer');

UPDATE "Cash_Register_Session" SET "closing_cash_actual_minor"=money_to_units("closing_cash_actual",100);

INSERT INTO Money_Migration_Evidence SELECT 'Cash_Register_Session','closing_cash_actual',COUNT(*),100,COALESCE(SUM("closing_cash_actual_minor"),0),COALESCE(SUM(CASE WHEN "closing_cash_actual" != "closing_cash_actual_minor"/100.0 THEN 1 ELSE 0 END),0) FROM "Cash_Register_Session";

UPDATE "Cash_Register_Session" SET "closing_cash_actual"="closing_cash_actual_minor"/100.0;

ALTER TABLE "Cash_Register_Session" ADD COLUMN "expected_cash_system_minor" INTEGER CHECK("expected_cash_system_minor" IS NULL OR typeof("expected_cash_system_minor")='integer');

UPDATE "Cash_Register_Session" SET "expected_cash_system_minor"=money_to_units("expected_cash_system",100);

INSERT INTO Money_Migration_Evidence SELECT 'Cash_Register_Session','expected_cash_system',COUNT(*),100,COALESCE(SUM("expected_cash_system_minor"),0),COALESCE(SUM(CASE WHEN "expected_cash_system" != "expected_cash_system_minor"/100.0 THEN 1 ELSE 0 END),0) FROM "Cash_Register_Session";

UPDATE "Cash_Register_Session" SET "expected_cash_system"="expected_cash_system_minor"/100.0;

ALTER TABLE "Cash_Register_Session" ADD COLUMN "cash_discrepancy_minor" INTEGER CHECK("cash_discrepancy_minor" IS NULL OR typeof("cash_discrepancy_minor")='integer');

UPDATE "Cash_Register_Session" SET "cash_discrepancy_minor"=money_to_units("cash_discrepancy",100);

INSERT INTO Money_Migration_Evidence SELECT 'Cash_Register_Session','cash_discrepancy',COUNT(*),100,COALESCE(SUM("cash_discrepancy_minor"),0),COALESCE(SUM(CASE WHEN "cash_discrepancy" != "cash_discrepancy_minor"/100.0 THEN 1 ELSE 0 END),0) FROM "Cash_Register_Session";

UPDATE "Cash_Register_Session" SET "cash_discrepancy"="cash_discrepancy_minor"/100.0;

CREATE TRIGGER money_Cash_Register_Session_insert AFTER INSERT ON "Cash_Register_Session"
BEGIN UPDATE "Cash_Register_Session" SET "opening_cash_minor"=money_to_units(NEW."opening_cash",100),"opening_cash"=money_to_units(NEW."opening_cash",100)/100.0,"closing_cash_actual_minor"=money_to_units(NEW."closing_cash_actual",100),"closing_cash_actual"=money_to_units(NEW."closing_cash_actual",100)/100.0,"expected_cash_system_minor"=money_to_units(NEW."expected_cash_system",100),"expected_cash_system"=money_to_units(NEW."expected_cash_system",100)/100.0,"cash_discrepancy_minor"=money_to_units(NEW."cash_discrepancy",100),"cash_discrepancy"=money_to_units(NEW."cash_discrepancy",100)/100.0 WHERE rowid=NEW.rowid; END;

CREATE TRIGGER money_Cash_Register_Session_update AFTER UPDATE OF "opening_cash","closing_cash_actual","expected_cash_system","cash_discrepancy" ON "Cash_Register_Session"
BEGIN UPDATE "Cash_Register_Session" SET "opening_cash_minor"=money_to_units(NEW."opening_cash",100),"opening_cash"=money_to_units(NEW."opening_cash",100)/100.0,"closing_cash_actual_minor"=money_to_units(NEW."closing_cash_actual",100),"closing_cash_actual"=money_to_units(NEW."closing_cash_actual",100)/100.0,"expected_cash_system_minor"=money_to_units(NEW."expected_cash_system",100),"expected_cash_system"=money_to_units(NEW."expected_cash_system",100)/100.0,"cash_discrepancy_minor"=money_to_units(NEW."cash_discrepancy",100),"cash_discrepancy"=money_to_units(NEW."cash_discrepancy",100)/100.0 WHERE rowid=NEW.rowid; END;

CREATE TRIGGER money_Cash_Register_Session_guard BEFORE UPDATE OF "opening_cash_minor","closing_cash_actual_minor","expected_cash_system_minor","cash_discrepancy_minor" ON "Cash_Register_Session"
WHEN NEW."opening_cash_minor" IS NOT money_to_units(NEW."opening_cash",100) OR NEW."closing_cash_actual_minor" IS NOT money_to_units(NEW."closing_cash_actual",100) OR NEW."expected_cash_system_minor" IS NOT money_to_units(NEW."expected_cash_system",100) OR NEW."cash_discrepancy_minor" IS NOT money_to_units(NEW."cash_discrepancy",100)
BEGIN SELECT RAISE(ABORT,'Integer money and compatibility values must agree'); END;

ALTER TABLE "Cash_Movement" ADD COLUMN "amount_minor" INTEGER CHECK("amount_minor" IS NULL OR typeof("amount_minor")='integer');

UPDATE "Cash_Movement" SET "amount_minor"=money_to_units("amount",100);

INSERT INTO Money_Migration_Evidence SELECT 'Cash_Movement','amount',COUNT(*),100,COALESCE(SUM("amount_minor"),0),COALESCE(SUM(CASE WHEN "amount" != "amount_minor"/100.0 THEN 1 ELSE 0 END),0) FROM "Cash_Movement";

UPDATE "Cash_Movement" SET "amount"="amount_minor"/100.0;

CREATE TRIGGER money_Cash_Movement_insert AFTER INSERT ON "Cash_Movement"
BEGIN UPDATE "Cash_Movement" SET "amount_minor"=money_to_units(NEW."amount",100),"amount"=money_to_units(NEW."amount",100)/100.0 WHERE rowid=NEW.rowid; END;

CREATE TRIGGER money_Cash_Movement_update AFTER UPDATE OF "amount" ON "Cash_Movement"
BEGIN UPDATE "Cash_Movement" SET "amount_minor"=money_to_units(NEW."amount",100),"amount"=money_to_units(NEW."amount",100)/100.0 WHERE rowid=NEW.rowid; END;

CREATE TRIGGER money_Cash_Movement_guard BEFORE UPDATE OF "amount_minor" ON "Cash_Movement"
WHEN NEW."amount_minor" IS NOT money_to_units(NEW."amount",100)
BEGIN SELECT RAISE(ABORT,'Integer money and compatibility values must agree'); END;

ALTER TABLE "Customer_Returns" ADD COLUMN "refund_amount_minor" INTEGER CHECK("refund_amount_minor" IS NULL OR typeof("refund_amount_minor")='integer');

UPDATE "Customer_Returns" SET "refund_amount_minor"=money_to_units("refund_amount",100);

INSERT INTO Money_Migration_Evidence SELECT 'Customer_Returns','refund_amount',COUNT(*),100,COALESCE(SUM("refund_amount_minor"),0),COALESCE(SUM(CASE WHEN "refund_amount" != "refund_amount_minor"/100.0 THEN 1 ELSE 0 END),0) FROM "Customer_Returns";

UPDATE "Customer_Returns" SET "refund_amount"="refund_amount_minor"/100.0;

CREATE TRIGGER money_Customer_Returns_insert AFTER INSERT ON "Customer_Returns"
BEGIN UPDATE "Customer_Returns" SET "refund_amount_minor"=money_to_units(NEW."refund_amount",100),"refund_amount"=money_to_units(NEW."refund_amount",100)/100.0 WHERE rowid=NEW.rowid; END;

CREATE TRIGGER money_Customer_Returns_update AFTER UPDATE OF "refund_amount" ON "Customer_Returns"
BEGIN UPDATE "Customer_Returns" SET "refund_amount_minor"=money_to_units(NEW."refund_amount",100),"refund_amount"=money_to_units(NEW."refund_amount",100)/100.0 WHERE rowid=NEW.rowid; END;

CREATE TRIGGER money_Customer_Returns_guard BEFORE UPDATE OF "refund_amount_minor" ON "Customer_Returns"
WHEN NEW."refund_amount_minor" IS NOT money_to_units(NEW."refund_amount",100)
BEGIN SELECT RAISE(ABORT,'Integer money and compatibility values must agree'); END;

ALTER TABLE "Return_Items" ADD COLUMN "unit_price_minor" INTEGER CHECK("unit_price_minor" IS NULL OR typeof("unit_price_minor")='integer');

UPDATE "Return_Items" SET "unit_price_minor"=money_to_units("unit_price",100000000);

INSERT INTO Money_Migration_Evidence SELECT 'Return_Items','unit_price',COUNT(*),100000000,COALESCE(SUM("unit_price_minor"),0),COALESCE(SUM(CASE WHEN "unit_price" != "unit_price_minor"/100000000.0 THEN 1 ELSE 0 END),0) FROM "Return_Items";

UPDATE "Return_Items" SET "unit_price"="unit_price_minor"/100000000.0;

ALTER TABLE "Return_Items" ADD COLUMN "subtotal_minor" INTEGER CHECK("subtotal_minor" IS NULL OR typeof("subtotal_minor")='integer');

UPDATE "Return_Items" SET "subtotal_minor"=money_to_units("subtotal",100000000);

INSERT INTO Money_Migration_Evidence SELECT 'Return_Items','subtotal',COUNT(*),100000000,COALESCE(SUM("subtotal_minor"),0),COALESCE(SUM(CASE WHEN "subtotal" != "subtotal_minor"/100000000.0 THEN 1 ELSE 0 END),0) FROM "Return_Items";

UPDATE "Return_Items" SET "subtotal"="subtotal_minor"/100000000.0;

CREATE TRIGGER money_Return_Items_insert AFTER INSERT ON "Return_Items"
BEGIN UPDATE "Return_Items" SET "unit_price_minor"=money_to_units(NEW."unit_price",100000000),"unit_price"=money_to_units(NEW."unit_price",100000000)/100000000.0,"subtotal_minor"=money_to_units(NEW."subtotal",100000000),"subtotal"=money_to_units(NEW."subtotal",100000000)/100000000.0 WHERE rowid=NEW.rowid; END;

CREATE TRIGGER money_Return_Items_update AFTER UPDATE OF "unit_price","subtotal" ON "Return_Items"
BEGIN UPDATE "Return_Items" SET "unit_price_minor"=money_to_units(NEW."unit_price",100000000),"unit_price"=money_to_units(NEW."unit_price",100000000)/100000000.0,"subtotal_minor"=money_to_units(NEW."subtotal",100000000),"subtotal"=money_to_units(NEW."subtotal",100000000)/100000000.0 WHERE rowid=NEW.rowid; END;

CREATE TRIGGER money_Return_Items_guard BEFORE UPDATE OF "unit_price_minor","subtotal_minor" ON "Return_Items"
WHEN NEW."unit_price_minor" IS NOT money_to_units(NEW."unit_price",100000000) OR NEW."subtotal_minor" IS NOT money_to_units(NEW."subtotal",100000000)
BEGIN SELECT RAISE(ABORT,'Integer money and compatibility values must agree'); END;

ALTER TABLE "Credit_Payment" ADD COLUMN "amount_minor" INTEGER CHECK("amount_minor" IS NULL OR typeof("amount_minor")='integer');

UPDATE "Credit_Payment" SET "amount_minor"=money_to_units("amount",100);

INSERT INTO Money_Migration_Evidence SELECT 'Credit_Payment','amount',COUNT(*),100,COALESCE(SUM("amount_minor"),0),COALESCE(SUM(CASE WHEN "amount" != "amount_minor"/100.0 THEN 1 ELSE 0 END),0) FROM "Credit_Payment";

UPDATE "Credit_Payment" SET "amount"="amount_minor"/100.0;

CREATE TRIGGER money_Credit_Payment_insert AFTER INSERT ON "Credit_Payment"
BEGIN UPDATE "Credit_Payment" SET "amount_minor"=money_to_units(NEW."amount",100),"amount"=money_to_units(NEW."amount",100)/100.0 WHERE rowid=NEW.rowid; END;

CREATE TRIGGER money_Credit_Payment_update AFTER UPDATE OF "amount" ON "Credit_Payment"
BEGIN UPDATE "Credit_Payment" SET "amount_minor"=money_to_units(NEW."amount",100),"amount"=money_to_units(NEW."amount",100)/100.0 WHERE rowid=NEW.rowid; END;

CREATE TRIGGER money_Credit_Payment_guard BEFORE UPDATE OF "amount_minor" ON "Credit_Payment"
WHEN NEW."amount_minor" IS NOT money_to_units(NEW."amount",100)
BEGIN SELECT RAISE(ABORT,'Integer money and compatibility values must agree'); END;

ALTER TABLE "Refund_Transaction" ADD COLUMN "amount_minor" INTEGER CHECK("amount_minor" IS NULL OR typeof("amount_minor")='integer');

UPDATE "Refund_Transaction" SET "amount_minor"=money_to_units("amount",100);

INSERT INTO Money_Migration_Evidence SELECT 'Refund_Transaction','amount',COUNT(*),100,COALESCE(SUM("amount_minor"),0),COALESCE(SUM(CASE WHEN "amount" != "amount_minor"/100.0 THEN 1 ELSE 0 END),0) FROM "Refund_Transaction";

UPDATE "Refund_Transaction" SET "amount"="amount_minor"/100.0;

CREATE TRIGGER money_Refund_Transaction_insert AFTER INSERT ON "Refund_Transaction"
BEGIN UPDATE "Refund_Transaction" SET "amount_minor"=money_to_units(NEW."amount",100),"amount"=money_to_units(NEW."amount",100)/100.0 WHERE rowid=NEW.rowid; END;

CREATE TRIGGER money_Refund_Transaction_update AFTER UPDATE OF "amount" ON "Refund_Transaction"
BEGIN UPDATE "Refund_Transaction" SET "amount_minor"=money_to_units(NEW."amount",100),"amount"=money_to_units(NEW."amount",100)/100.0 WHERE rowid=NEW.rowid; END;

CREATE TRIGGER money_Refund_Transaction_guard BEFORE UPDATE OF "amount_minor" ON "Refund_Transaction"
WHEN NEW."amount_minor" IS NOT money_to_units(NEW."amount",100)
BEGIN SELECT RAISE(ABORT,'Integer money and compatibility values must agree'); END;

ALTER TABLE "Credit_Payment_Operation" ADD COLUMN "amount_minor" INTEGER CHECK("amount_minor" IS NULL OR typeof("amount_minor")='integer');

UPDATE "Credit_Payment_Operation" SET "amount_minor"=money_to_units("amount",100);

INSERT INTO Money_Migration_Evidence SELECT 'Credit_Payment_Operation','amount',COUNT(*),100,COALESCE(SUM("amount_minor"),0),COALESCE(SUM(CASE WHEN "amount" != "amount_minor"/100.0 THEN 1 ELSE 0 END),0) FROM "Credit_Payment_Operation";

UPDATE "Credit_Payment_Operation" SET "amount"="amount_minor"/100.0;

ALTER TABLE "Credit_Payment_Operation" ADD COLUMN "balance_after_minor" INTEGER CHECK("balance_after_minor" IS NULL OR typeof("balance_after_minor")='integer');

UPDATE "Credit_Payment_Operation" SET "balance_after_minor"=money_to_units("balance_after",100);

INSERT INTO Money_Migration_Evidence SELECT 'Credit_Payment_Operation','balance_after',COUNT(*),100,COALESCE(SUM("balance_after_minor"),0),COALESCE(SUM(CASE WHEN "balance_after" != "balance_after_minor"/100.0 THEN 1 ELSE 0 END),0) FROM "Credit_Payment_Operation";

UPDATE "Credit_Payment_Operation" SET "balance_after"="balance_after_minor"/100.0;

CREATE TRIGGER money_Credit_Payment_Operation_insert AFTER INSERT ON "Credit_Payment_Operation"
BEGIN UPDATE "Credit_Payment_Operation" SET "amount_minor"=money_to_units(NEW."amount",100),"amount"=money_to_units(NEW."amount",100)/100.0,"balance_after_minor"=money_to_units(NEW."balance_after",100),"balance_after"=money_to_units(NEW."balance_after",100)/100.0 WHERE rowid=NEW.rowid; END;

CREATE TRIGGER money_Credit_Payment_Operation_update AFTER UPDATE OF "amount","balance_after" ON "Credit_Payment_Operation"
BEGIN UPDATE "Credit_Payment_Operation" SET "amount_minor"=money_to_units(NEW."amount",100),"amount"=money_to_units(NEW."amount",100)/100.0,"balance_after_minor"=money_to_units(NEW."balance_after",100),"balance_after"=money_to_units(NEW."balance_after",100)/100.0 WHERE rowid=NEW.rowid; END;

CREATE TRIGGER money_Credit_Payment_Operation_guard BEFORE UPDATE OF "amount_minor","balance_after_minor" ON "Credit_Payment_Operation"
WHEN NEW."amount_minor" IS NOT money_to_units(NEW."amount",100) OR NEW."balance_after_minor" IS NOT money_to_units(NEW."balance_after",100)
BEGIN SELECT RAISE(ABORT,'Integer money and compatibility values must agree'); END;

ALTER TABLE "Credit_Payment_Reversal" ADD COLUMN "amount_minor" INTEGER CHECK("amount_minor" IS NULL OR typeof("amount_minor")='integer');

UPDATE "Credit_Payment_Reversal" SET "amount_minor"=money_to_units("amount",100);

INSERT INTO Money_Migration_Evidence SELECT 'Credit_Payment_Reversal','amount',COUNT(*),100,COALESCE(SUM("amount_minor"),0),COALESCE(SUM(CASE WHEN "amount" != "amount_minor"/100.0 THEN 1 ELSE 0 END),0) FROM "Credit_Payment_Reversal";

UPDATE "Credit_Payment_Reversal" SET "amount"="amount_minor"/100.0;

CREATE TRIGGER money_Credit_Payment_Reversal_insert AFTER INSERT ON "Credit_Payment_Reversal"
BEGIN UPDATE "Credit_Payment_Reversal" SET "amount_minor"=money_to_units(NEW."amount",100),"amount"=money_to_units(NEW."amount",100)/100.0 WHERE rowid=NEW.rowid; END;

CREATE TRIGGER money_Credit_Payment_Reversal_update AFTER UPDATE OF "amount" ON "Credit_Payment_Reversal"
BEGIN UPDATE "Credit_Payment_Reversal" SET "amount_minor"=money_to_units(NEW."amount",100),"amount"=money_to_units(NEW."amount",100)/100.0 WHERE rowid=NEW.rowid; END;

CREATE TRIGGER money_Credit_Payment_Reversal_guard BEFORE UPDATE OF "amount_minor" ON "Credit_Payment_Reversal"
WHEN NEW."amount_minor" IS NOT money_to_units(NEW."amount",100)
BEGIN SELECT RAISE(ABORT,'Integer money and compatibility values must agree'); END;

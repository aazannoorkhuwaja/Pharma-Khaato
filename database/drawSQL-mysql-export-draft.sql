-- ==========================================
-- 1. CREATE TABLES
-- ==========================================

CREATE TABLE `Customers`(
    `id_card_number` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
    `first_name` TEXT NOT NULL,
    `last_name` TEXT NOT NULL,
    `Email_Address` LONGTEXT NOT NULL,
    `city` TEXT NOT NULL,
    `registration_date` DATE NOT NULL
);

CREATE TABLE `Employee`(
    `Employee_id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
    `First_name` TEXT NOT NULL,
    `Last_name` TEXT NOT NULL,
    `occupation` TEXT NOT NULL
);

CREATE TABLE `Purchase`(
    `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
    `number_of_products` BIGINT NOT NULL,
    `total_price` DECIMAL(10, 2) NOT NULL,
    `price_with_tax` DECIMAL(10, 2) NOT NULL,
    `customer_id` BIGINT UNSIGNED NOT NULL,
    `employee_id` BIGINT UNSIGNED NOT NULL,
    `payment_method` TEXT NOT NULL,
    `discount_amount` DECIMAL(10, 2) NOT NULL
);

CREATE TABLE `Receipt`(
    `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
    `printing_date` DATE NOT NULL,
    `time` TIME NOT NULL,
    `purchase_id` BIGINT UNSIGNED NOT NULL,
    `number_of_items` BIGINT NOT NULL
);

CREATE TABLE `Customer_Khatoo`(
    `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
    `amount_paid` DECIMAL(10, 2) NOT NULL,
    `amount_due` DECIMAL(10, 2) NOT NULL,
    `purchase_id` BIGINT UNSIGNED NOT NULL,
    `customer_id` BIGINT UNSIGNED NOT NULL,
    `payment_method` TEXT NOT NULL
);

CREATE TABLE `Supplier`(
    `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
    `supplier_name` TEXT NOT NULL,
    `supplier_company_name` TEXT NOT NULL,
    `Email_address` TEXT NOT NULL,
    `phone_number` VARCHAR(15) NOT NULL
);

CREATE TABLE `Products`(
    `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
    `product_name` TEXT NOT NULL,
    `company_name` TEXT NOT NULL,
    `category` TEXT NOT NULL,
    `price` DECIMAL(10, 2) NOT NULL,
    `stock_quantity` BIGINT NOT NULL,
    `min_stock` BIGINT NOT NULL,
    `formula` VARCHAR(255) NOT NULL
);

CREATE TABLE `Batch`(
    `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
    `number_of_product` BIGINT NOT NULL,
    `expiry_date` DATE NOT NULL,
    `product_id` BIGINT UNSIGNED NOT NULL,
    `supplier_id` BIGINT UNSIGNED NOT NULL,
    `quantity` BIGINT NOT NULL,
    `manufacture_Date` DATE NOT NULL
);

CREATE TABLE `Sales_details`(
    `purchase_id` BIGINT UNSIGNED NOT NULL,
    `batch_id` BIGINT UNSIGNED NOT NULL,
    `Quantity` BIGINT NOT NULL,
    PRIMARY KEY(`purchase_id`, `batch_id`)
);

-- ==========================================
-- 2. FOREIGN KEYS
-- ==========================================

ALTER TABLE `Purchase` ADD CONSTRAINT `purchase_customer_id_foreign` FOREIGN KEY(`customer_id`) REFERENCES `Customers`(`id_card_number`);
ALTER TABLE `Purchase` ADD CONSTRAINT `purchase_employee_id_foreign` FOREIGN KEY(`employee_id`) REFERENCES `Employee`(`Employee_id`);

ALTER TABLE `Receipt` ADD CONSTRAINT `receipt_purchase_id_foreign` FOREIGN KEY(`purchase_id`) REFERENCES `Purchase`(`id`);

ALTER TABLE `Customer_Khatoo` ADD CONSTRAINT `customer_khatoo_customer_id_foreign` FOREIGN KEY(`customer_id`) REFERENCES `Customers`(`id_card_number`);
ALTER TABLE `Customer_Khatoo` ADD CONSTRAINT `customer_khatoo_purchase_id_foreign` FOREIGN KEY(`purchase_id`) REFERENCES `Purchase`(`id`);

ALTER TABLE `Batch` ADD CONSTRAINT `batch_product_id_foreign` FOREIGN KEY(`product_id`) REFERENCES `Products`(`id`);
ALTER TABLE `Batch` ADD CONSTRAINT `batch_supplier_id_foreign` FOREIGN KEY(`supplier_id`) REFERENCES `Supplier`(`id`);

ALTER TABLE `Sales_details` ADD CONSTRAINT `sales_purchase_id_foreign` FOREIGN KEY(`purchase_id`) REFERENCES `Purchase`(`id`);
ALTER TABLE `Sales_details` ADD CONSTRAINT `sales_batch_id_foreign` FOREIGN KEY(`batch_id`) REFERENCES `Batch`(`id`);

-- ==========================================
-- 3. POPULATE DATA
-- ==========================================

INSERT INTO `Customers` (`first_name`, `last_name`, `Email_Address`, `city`, `registration_date`) VALUES
('Ahmed', 'Khan', 'ahmed.k@email.com', 'Peshawar', '2026-01-10'),
('Sara', 'Ali', 'sara.a@email.com', 'Islamabad', '2026-02-15');

INSERT INTO `Employee` (`First_name`, `Last_name`, `occupation`) VALUES
('Usman', 'Yousaf', 'Pharmacist'),
('Zainab', 'Malik', 'Sales Assistant');

INSERT INTO `Supplier` (`supplier_name`, `supplier_company_name`, `Email_address`, `phone_number`) VALUES
('MediDistro', 'National Pharma Ltd', 'contact@natpharma.pk', '03001234567');

INSERT INTO `Products` (`product_name`, `company_name`, `category`, `price`, `stock_quantity`, `min_stock`, `formula`) VALUES
('Panadol', 'GSK', 'Analgesic', 50.00, 1000, 100, 'Paracetamol 500mg'),
('Augmentin', 'GSK', 'Antibiotic', 450.00, 200, 20, 'Amoxicillin + Clavulanate');

INSERT INTO `Batch` (`id`, `number_of_product`, `expiry_date`, `product_id`, `supplier_id`, `quantity`, `manufacture_Date`) VALUES
(1, 100, '2028-05-01', 1, 1, 100, '2026-01-01'),
(2, 50, '2027-12-15', 2, 1, 50, '2025-12-01');

INSERT INTO `Purchase` (`id`, `number_of_products`, `total_price`, `price_with_tax`, `customer_id`, `employee_id`, `payment_method`, `discount_amount`) VALUES
(1, 5, 250.00, 275.00, 1, 1, 'Cash', 0.00),
(2, 2, 900.00, 990.00, 2, 1, 'Card', 50.00);

INSERT INTO `Sales_details` (`purchase_id`, `batch_id`, `Quantity`) VALUES
(1, 1, 5),
(2, 2, 2);

INSERT INTO `Receipt` (`printing_date`, `time`, `purchase_id`, `number_of_items`) VALUES
('2026-04-28', '10:30:00', 1, 5),
('2026-04-28', '11:45:00', 2, 2);

INSERT INTO `Customer_Khatoo` (`amount_paid`, `amount_due`, `purchase_id`, `customer_id`, `payment_method`) VALUES
(275.00, 0.00, 1, 1, 'Cash'),
(500.00, 490.00, 2, 2, 'Card');

CREATE TABLE `Customers`(
    `id_card_number` BIGINT UNSIGNED NOT NULL PRIMARY KEY,
    `first_name` TEXT NOT NULL,
    `last_name` TEXT NOT NULL,
    `Email_Address` LONGTEXT NOT NULL,
    `city` TEXT NOT NULL,
    `registration_date` DATE NOT NULL
);
CREATE TABLE `Employee`(
    `Employee_id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
    `First_name` TEXT NOT NULL,
    `Last_name` TEXT NOT NULL
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
    `printing_date` DATETIME NOT NULL, 
    `purchase_id` BIGINT UNSIGNED NOT NULL, 
    `number_of_items` BIGINT NOT NULL
);
CREATE TABLE `Customer_Khatoo`(
    `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
    `amount_paid` DECIMAL(10, 2) NOT NULL,
    `amount_due` DECIMAL(10, 2) NOT NULL,
    `purchase_id` BIGINT UNSIGNED NULL,
    `customer_id` BIGINT UNSIGNED NOT NULL,
    `payment_method` TEXT NOT NULL
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
CREATE TABLE `Sales_details`(
    `purchase_id` BIGINT UNSIGNED NOT NULL,
    `batch_id` BIGINT UNSIGNED NOT NULL,
    `Quantity` BIGINT NOT NULL,
    PRIMARY KEY(`purchase_id`,`batch_id`),
    FOREIGN KEY(`purchase_id`) REFERENCES `Purchase`(`id`),
    FOREIGN KEY(`batch_id`) REFERENCES `Batch`(`id`)
);
CREATE TABLE `Supplier`(
    `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
    `supplier_name` TEXT NOT NULL,
    `supplier_company_name` TEXT NOT NULL,
    `Email_address` TEXT NOT NULL,
    `phone_number` VARCHAR(15) NOT NULL
);
ALTER TABLE
    `Customer_Khatoo` ADD CONSTRAINT `customer_khatoo_customer_id_foreign` FOREIGN KEY(`customer_id`) REFERENCES `Customers`(`id_card_number`);
ALTER TABLE
    `Purchase` ADD CONSTRAINT `purchase_employee_id_foreign` FOREIGN KEY(`employee_id`) REFERENCES `Employee`(`Employee_id`);
ALTER TABLE
    `Receipt` ADD CONSTRAINT `receipt_purchase_id_foreign` FOREIGN KEY(`purchase_id`) REFERENCES `Purchase`(`id`);
ALTER TABLE
    `Batch` ADD CONSTRAINT `batch_product_id_foreign` FOREIGN KEY(`product_id`) REFERENCES `Products`(`id`);
ALTER TABLE
    `Batch` ADD CONSTRAINT `batch_supplier_id_foreign` FOREIGN KEY(`supplier_id`) REFERENCES `Supplier`(`id`);
ALTER TABLE
    `Purchase` ADD CONSTRAINT `purchase_customer_id_foreign` FOREIGN KEY(`customer_id`) REFERENCES `Customers`(`id_card_number`);
ALTER TABLE
    `Customer_Khatoo` ADD CONSTRAINT `customer_khatoo_purchase_id_foreign` FOREIGN KEY(`purchase_id`) REFERENCES `Purchase`(`id`);

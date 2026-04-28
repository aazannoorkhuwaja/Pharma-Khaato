CREATE TABLE `Customers`(
    `id_card_number` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
    `first_name` TEXT NOT NULL,
    `last_name` TEXT NOT NULL,
    `khato_id` BIGINT NOT NULL,
    `Email_Address` LONGTEXT NOT NULL,
    `city` TEXT NOT NULL,
    `registration_date` DATE NOT NULL,
    `serving_employe_id` BIGINT NOT NULL
);
CREATE TABLE `Employee`(
    `Employee_id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
    `First_name` TEXT NOT NULL,
    `Last_name` TEXT NOT NULL
);
CREATE TABLE `Purchase`(
    `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
    `number_of_products` BIGINT NOT NULL,
    `total_price` FLOAT(53) NOT NULL,
    `price_with_tax` FLOAT(53) NOT NULL,
    `customer_id` BIGINT NOT NULL,
    `receipt_id` BIGINT NOT NULL
);
CREATE TABLE `Receipt`(
    `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
    `perchase_id` BIGINT NOT NULL,
    `printing_date` DATE NOT NULL,
    `time` TIME NOT NULL
);
CREATE TABLE `Customer_Khatoo`(
    `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
    `amount_paid` FLOAT(53) NOT NULL,
    `amount_due` FLOAT(53) NOT NULL,
    `khato_id` BIGINT NOT NULL
);
CREATE TABLE `Batch`(
    `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
    `number_of_product` BIGINT NOT NULL,
    `expiry_date` DATE NOT NULL,
    `product_id` BIGINT NOT NULL,
    `supplier_id` BIGINT NOT NULL,
    `quantity` BIGINT NOT NULL
);
CREATE TABLE `Products`(
    `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
    `product_name` TEXT NOT NULL,
    `company_name` TEXT NOT NULL,
    `category` TEXT NOT NULL,
    `price` BIGINT NOT NULL
);
CREATE TABLE `Sales_details`(
    `purchase_id` BIGINT NOT NULL,
    `batch_id` BIGINT NOT NULL,
    PRIMARY KEY(`purchase_id`)
);
ALTER TABLE
    `Sales_details` ADD PRIMARY KEY(`batch_id`);
CREATE TABLE `Supplier`(
    `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
    `supplier_name` TEXT NOT NULL,
    `supplier_company_name` TEXT NOT NULL,
    `Email_address` TEXT NOT NULL,
    `phone_number` BIGINT NOT NULL
);
ALTER TABLE
    `Purchase` ADD CONSTRAINT `purchase_id_foreign` FOREIGN KEY(`id`) REFERENCES `Customer_Khatoo`(`id`);
ALTER TABLE
    `Batch` ADD CONSTRAINT `batch_product_id_foreign` FOREIGN KEY(`product_id`) REFERENCES `Products`(`id`);
ALTER TABLE
    `Batch` ADD CONSTRAINT `batch_supplier_id_foreign` FOREIGN KEY(`supplier_id`) REFERENCES `Supplier`(`id`);
ALTER TABLE
    `Purchase` ADD CONSTRAINT `purchase_receipt_id_foreign` FOREIGN KEY(`receipt_id`) REFERENCES `Receipt`(`id`);
ALTER TABLE
    `Purchase` ADD CONSTRAINT `purchase_customer_id_foreign` FOREIGN KEY(`customer_id`) REFERENCES `Customers`(`id_card_number`);
ALTER TABLE
    `Customers` ADD CONSTRAINT `customers_serving_employe_id_foreign` FOREIGN KEY(`serving_employe_id`) REFERENCES `Employee`(`Employee_id`);
ALTER TABLE
    `Batch` ADD CONSTRAINT `batch_id_foreign` FOREIGN KEY(`id`) REFERENCES `Sales_details`(`batch_id`);
ALTER TABLE
    `Purchase` ADD CONSTRAINT `purchase_id_foreign` FOREIGN KEY(`id`) REFERENCES `Sales_details`(`purchase_id`);
-- ============================================================
-- Pharma-Khaato Canonical MySQL Database Schema & Seed Data
-- ============================================================

CREATE TABLE IF NOT EXISTS `Customers` (
    `id_card_number` VARCHAR(15) NOT NULL PRIMARY KEY,
    `first_name` VARCHAR(100) NOT NULL,
    `last_name` VARCHAR(100) NOT NULL,
    `Email_Address` VARCHAR(255) NOT NULL DEFAULT 'N/A',
    `city` VARCHAR(100) NOT NULL DEFAULT 'N/A',
    `registration_date` DATE NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS `Employee` (
    `Employee_id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
    `username` VARCHAR(50) NOT NULL UNIQUE,
    `password` VARCHAR(255) NOT NULL,
    `First_name` VARCHAR(100) NOT NULL,
    `Last_name` VARCHAR(100) NOT NULL,
    `occupation` VARCHAR(50) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS `Supplier` (
    `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
    `supplier_name` VARCHAR(150) NOT NULL,
    `supplier_company_name` VARCHAR(150) NOT NULL,
    `Email_address` VARCHAR(255) NOT NULL,
    `phone_number` VARCHAR(20) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS `Products` (
    `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
    `product_name` VARCHAR(150) NOT NULL,
    `company_name` VARCHAR(150) NOT NULL,
    `category` VARCHAR(100) NOT NULL,
    `price` DECIMAL(10, 2) NOT NULL,
    `stock_quantity` BIGINT NOT NULL DEFAULT 0,
    `min_stock` BIGINT NOT NULL DEFAULT 10,
    `formula` VARCHAR(255) NOT NULL DEFAULT 'N/A'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS `Batch` (
    `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
    `number_of_product` BIGINT NOT NULL,
    `expiry_date` DATE NOT NULL,
    `product_id` BIGINT UNSIGNED NOT NULL,
    `supplier_id` BIGINT UNSIGNED NOT NULL,
    `quantity` BIGINT NOT NULL,
    `manufacture_Date` DATE NOT NULL,
    FOREIGN KEY (`product_id`) REFERENCES `Products`(`id`) ON DELETE CASCADE,
    FOREIGN KEY (`supplier_id`) REFERENCES `Supplier`(`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS `Purchase` (
    `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
    `number_of_products` BIGINT NOT NULL,
    `total_price` DECIMAL(10, 2) NOT NULL,
    `price_with_tax` DECIMAL(10, 2) NOT NULL,
    `customer_id` VARCHAR(15) NOT NULL,
    `employee_id` BIGINT UNSIGNED NOT NULL,
    `payment_method` VARCHAR(50) NOT NULL,
    `discount_amount` DECIMAL(10, 2) NOT NULL DEFAULT 0.00,
    FOREIGN KEY (`customer_id`) REFERENCES `Customers`(`id_card_number`) ON DELETE CASCADE,
    FOREIGN KEY (`employee_id`) REFERENCES `Employee`(`Employee_id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS `Receipt` (
    `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
    `printing_date` DATE NOT NULL,
    `time` TIME NOT NULL,
    `purchase_id` BIGINT UNSIGNED NOT NULL,
    `number_of_items` BIGINT NOT NULL,
    FOREIGN KEY (`purchase_id`) REFERENCES `Purchase`(`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS `Customer_Khatoo` (
    `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
    `amount_paid` DECIMAL(10, 2) NOT NULL DEFAULT 0.00,
    `amount_due` DECIMAL(10, 2) NOT NULL DEFAULT 0.00,
    `purchase_id` BIGINT UNSIGNED NOT NULL,
    `customer_id` VARCHAR(15) NOT NULL,
    `payment_method` VARCHAR(50) NOT NULL,
    FOREIGN KEY (`customer_id`) REFERENCES `Customers`(`id_card_number`) ON DELETE CASCADE,
    FOREIGN KEY (`purchase_id`) REFERENCES `Purchase`(`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS `Sales_details` (
    `purchase_id` BIGINT UNSIGNED NOT NULL,
    `batch_id` BIGINT UNSIGNED NOT NULL,
    `Quantity` BIGINT NOT NULL,
    PRIMARY KEY (`purchase_id`, `batch_id`),
    FOREIGN KEY (`purchase_id`) REFERENCES `Purchase`(`id`) ON DELETE CASCADE,
    FOREIGN KEY (`batch_id`) REFERENCES `Batch`(`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ============================================================
-- DEFAULT SEED DATA
-- ============================================================

-- Default Employees (Passwords hashed with SHA-256)
-- admin: admin123 -> 240be518fabd2724ddb6f04eeb1da5967448d7e831c08c8fa822809f74c720a9
-- pharmacist: pharm123 -> 55210e7b8a7b97a228383e58988636b1edb7d34cf4b5f90d56ee2569e5d4cb31
-- sales: sales123 -> c30353c7a36f6d0f5bb8ec2b64d008407f6f1406e12e3e606ee3fa265a6f0592
INSERT INTO `Employee` (`Employee_id`, `username`, `password`, `First_name`, `Last_name`, `occupation`) VALUES
(1, 'admin', '240be518fabd2724ddb6f04eeb1da5967448d7e831c08c8fa822809f74c720a9', 'Usman', 'Yousaf', 'Admin'),
(2, 'pharmacist', '55210e7b8a7b97a228383e58988636b1edb7d34cf4b5f90d56ee2569e5d4cb31', 'Atif', 'Khan', 'Pharmacist'),
(3, 'salesman', 'c30353c7a36f6d0f5bb8ec2b64d008407f6f1406e12e3e606ee3fa265a6f0592', 'Zainab', 'Malik', 'Sales Assistant')
ON DUPLICATE KEY UPDATE `username`=`username`;

-- Default Customers
INSERT INTO `Customers` (`id_card_number`, `first_name`, `last_name`, `Email_Address`, `city`, `registration_date`) VALUES
('3520212345671', 'Ahmed', 'Khan', 'ahmed.k@email.com', 'Peshawar', '2026-01-10'),
('3520212345672', 'Sara', 'Ali', 'sara.a@email.com', 'Islamabad', '2026-02-15')
ON DUPLICATE KEY UPDATE `first_name`=`first_name`;

-- Default Suppliers
INSERT INTO `Supplier` (`id`, `supplier_name`, `supplier_company_name`, `Email_address`, `phone_number`) VALUES
(1, 'MediDistro', 'National Pharma Ltd', 'contact@natpharma.pk', '03001234567'),
(2, 'BioMed Supplies', 'BioMed Corp', 'sales@biomed.pk', '03219876543')
ON DUPLICATE KEY UPDATE `id`=`id`;

-- Default Products
INSERT INTO `Products` (`id`, `product_name`, `company_name`, `category`, `price`, `stock_quantity`, `min_stock`, `formula`) VALUES
(1, 'Panadol 500mg', 'GSK', 'Analgesic', 50.00, 1000, 100, 'Paracetamol 500mg'),
(2, 'Augmentin 625mg', 'GSK', 'Antibiotic', 450.00, 200, 20, 'Amoxicillin + Clavulanate'),
(3, 'Brufen 400mg', 'Abbott', 'NSAID', 80.00, 500, 50, 'Ibuprofen 400mg'),
(4, 'Disprin 300mg', 'Reckitt', 'Analgesic', 30.00, 300, 30, 'Aspirin 300mg')
ON DUPLICATE KEY UPDATE `id`=`id`;

-- Default Batches
INSERT INTO `Batch` (`id`, `number_of_product`, `expiry_date`, `product_id`, `supplier_id`, `quantity`, `manufacture_Date`) VALUES
(1, 1000, '2028-05-01', 1, 1, 1000, '2026-01-01'),
(2, 200, '2027-12-15', 2, 1, 200, '2025-12-01'),
(3, 500, '2027-08-20', 3, 2, 500, '2026-02-10'),
(4, 300, '2026-09-01', 4, 2, 300, '2025-09-01')
ON DUPLICATE KEY UPDATE `id`=`id`;

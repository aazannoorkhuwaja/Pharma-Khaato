# 🏥 Pharma-Khaato

> **Surgical Inventory & Credit Ledger (RDBMS)**

[![Python Version](https://img.shields.io/badge/Python-3.x-blue.svg)](https://python.org)
[![MySQL](https://img.shields.io/badge/MySQL-8.0+-orange.svg)](https://www.mysql.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](https://opensource.org/licenses/MIT)

Pharma-Khaato is a specialized Point of Sale (POS) system designed for surgical pharmacies. Built with Python and Tkinter, it provides an intuitive graphical interface tailored for pharmacy cashiers, store administrators, and inventory managers. 

It replaces manual, paper-based record-keeping by providing batch-specific inventory management and an automated traditional customer credit ledger (*Khaato*). The system enforces strict data integrity via a relational MySQL database, ensuring accurate running balance calculations, immutable audit trails for customer debt, and automated expiry-based stock alerts.

---

## ✨ Key Features

- 📦 **Batch-wise Inventory Control:** Manage individual medication batches, tracking stock quantities and expiry dates.
- 💳 **Automated Customer Ledger (Khaato):** Maintain and track outstanding customer credit dynamically without manual calculations.
- ⚡ **Real-time Stock Deduction & ACID Transactions:** Ensures stock is accurately deduced upon checkout, preventing overselling or data corruption.
- 🚨 **Expiry Date & Low-Stock Alerts:** Automated notifications prevent the sale of expired medicines and prompt timely restocking.
- 🧾 **Professional Thermal Receipts:** System-generated invoices detailing transactions, applied taxes (10% default), discounts, and sub-totals.

---

## 🛠️ Technology Stack

- **Frontend:** Python, CustomTkinter (for a modern, native desktop GUI)
- **Backend/Database:** MySQL (Relational Database Management System)
- **Database Driver:** `mysql-connector-python`
- **Data Manipulation:** `pandas`

---

## 🚀 Getting Started

### Prerequisites
- Python 3.x installed on your system.
- MySQL Server (Standalone or via XAMPP/WAMP/LAMP).

### 1. Clone the Repository
```bash
git clone https://github.com/aazannoorkhuwaja/Pharma-Khaato.git
cd Pharma-Khaato/project
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
# OR
pip install mysql-connector-python pandas customtkinter
```

### 3. Database Setup
The application requires a MySQL database. Create the database and user with the following SQL commands:

```sql
CREATE DATABASE pharmacy_db;
CREATE USER 'pharma'@'localhost' IDENTIFIED BY 'pharma123';
GRANT ALL PRIVILEGES ON pharmacy_db.* TO 'pharma'@'localhost';
FLUSH PRIVILEGES;
```

*Note: The application is designed to automatically attempt to initialize its tables using the provided SQL schema (`drawSQL-mysql-export-2026-04-26.sql`) upon first run.*

### 4. Run the Application
```bash
python main.py
```
*Alternatively, you can run the salesman module directly:*
```bash
python salesman_app.py
```

---

## ⚙️ Configuration

The application uses standard connection profiles but can be customized using Environment Variables. If you wish to use custom database credentials, set the following variables before running:

- `DB_HOST` (default: `localhost` / `127.0.0.1`)
- `DB_PORT` (default: `3306`)
- `DB_USER` (default: `pharma`)
- `DB_PASSWORD` (default: `pharma123`)
- `DB_NAME` (default: `pharmacy_db`)

---

## 📂 Documentation & Assets
Check the `docs/` folder for Entity-Relationship Diagrams (ERD) and project proposals.

---

## 👥 Core Team & Contributors

This project was developed as a university semester database project.

- **Aazan Noor Khuwaja** (Roll No: 24P-0581)
- **Atif Khan**
- **Uzair Shoaib**

---

## 📄 License
This project is licensed under the [MIT License](https://choosealicense.com/licenses/mit/).

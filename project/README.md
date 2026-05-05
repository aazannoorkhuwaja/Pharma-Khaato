# Pharmacy POS System

A desktop-based Point of Sale (POS) system for pharmacies built with Python, Tkinter, and MySQL.

## Features
- Customer Registration
- Billing System with Real-time Stock Updates
- Khatoo (Credit Ledger) Management
- Automated Tax Calculations (10%)

## Prerequisites
- Python 3.x
- MySQL Server

## Installation

1. **Clone the repository**:
   ```bash
   git clone <your-repo-url>
   cd DB-Project/project
   ```

2. **Install Dependencies**:
   ```bash
   pip install mysql-connector-python
   ```

3. **Database Setup**:
   - Create a database named `pharmacy_db`.
   - Import the schema using the provided SQL file:
     ```bash
     mysql -u root -p pharmacy_db < drawSQL-mysql-export-2026-04-26.sql
     ```
   - Create a user for the app:
     ```sql
     CREATE USER 'pharma'@'localhost' IDENTIFIED BY 'pharma123';
     GRANT ALL PRIVILEGES ON pharmacy_db.* TO 'pharma'@'localhost';
     FLUSH PRIVILEGES;
     ```

## Usage
Run the application using:
```bash
python main.py
```

## Environment Variables
If you want to use different database credentials, you can set the following environment variables:
- `DB_HOST` (default: localhost)
- `DB_USER` (default: pharma)
- `DB_PASS` (default: pharma123)
- `DB_NAME` (default: pharmacy_db)

## License
[MIT](https://choosealicense.com/licenses/mit/)

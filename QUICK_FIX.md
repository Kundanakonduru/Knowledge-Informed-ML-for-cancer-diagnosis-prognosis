# Quick Fix - Database Creation

## Problem
Database `cancer_diagnosis_db` doesn't exist, causing connection errors.

## Solution

### Option 1: Run the new setup script (Recommended)
```bash
python setup_and_run.py
```

This will:
1. Create the database
2. Run schema.sql
3. Import CSV data
4. Set up everything

### Option 2: Manual steps

#### Step 1: Create database
```bash
python backend/scripts/create_database.py
```

#### Step 2: Import data
```bash
python backend/scripts/setup_database.py
```

### Option 3: Using MySQL directly
```bash
mysql -u root -p < database/schema.sql
```

Then import data:
```bash
python backend/scripts/import_csv_to_db.py --data-dir data/
```

## What Was Fixed

1. ✅ **create_database.py** - New script to create database and run schema.sql
2. ✅ **setup_database.py** - Updated to handle database creation
3. ✅ **setup_and_run.py** - Updated to create database first

## Verify Setup

After running setup, verify:
```bash
# Check database exists
mysql -u root -p -e "SHOW DATABASES LIKE 'cancer_diagnosis_db';"

# Check tables
mysql -u root -p -e "USE cancer_diagnosis_db; SHOW TABLES;"

# Check data
mysql -u root -p -e "USE cancer_diagnosis_db; SELECT COUNT(*) FROM patients; SELECT COUNT(*) FROM omics_data;"
```

## Troubleshooting

### MySQL not running
```bash
# Windows
net start MySQL80

# Linux/Mac
sudo systemctl start mysql
# or
sudo service mysql start
```

### Wrong credentials
Edit `backend/.env` file:
```
DB_HOST=localhost
DB_USER=root
DB_PASSWORD=your_password
DB_NAME=cancer_diagnosis_db
DB_PORT=3306
```

### Permission denied
Make sure MySQL user has CREATE DATABASE privilege:
```sql
GRANT ALL PRIVILEGES ON *.* TO 'root'@'localhost';
FLUSH PRIVILEGES;
```

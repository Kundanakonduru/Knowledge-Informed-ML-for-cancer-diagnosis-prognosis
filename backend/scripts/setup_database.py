"""
Complete Database Setup Script
1. Creates database and tables
2. Imports all CSV files
3. Verifies data
"""

import sys
import os
from pathlib import Path
import subprocess
import pymysql
from sqlalchemy import create_engine, text

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

# Get database config
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_USER = os.getenv("DB_USER", "root")
DB_PASSWORD = os.getenv("DB_PASSWORD", "12345")
DB_NAME = os.getenv("DB_NAME", "cancer_diagnosis_db")
DB_PORT = int(os.getenv("DB_PORT", 3306))

from database.connection import init_db, engine
from database.models import Base
from scripts.import_csv_to_db import import_all_csv_files

def create_database_if_not_exists():
    """
    Create database if it doesn't exist
    """
    try:
        # Connect to MySQL without specifying database
        connection = pymysql.connect(
            host=DB_HOST,
            user=DB_USER,
            password=DB_PASSWORD,
            port=DB_PORT
        )
        
        with connection.cursor() as cursor:
            # Create database if not exists
            cursor.execute(f"CREATE DATABASE IF NOT EXISTS {DB_NAME} CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
            print(f"✅ Database '{DB_NAME}' created/verified")
        
        connection.close()
        return True
    except Exception as e:
        print(f"❌ Error creating database: {str(e)}")
        print(f"   Please check MySQL is running and credentials are correct")
        return False

def run_schema_sql():
    """
    Alternative: Run schema.sql file directly using MySQL
    This is more reliable as it uses the exact schema
    """
    try:
        project_root = Path(__file__).parent.parent.parent
        schema_file = project_root / "database" / "schema.sql"
        
        if not schema_file.exists():
            print(f"⚠️  Schema file not found: {schema_file}")
            return False
        
        print(f"📄 Running schema.sql file...")
        
        # Read schema file
        with open(schema_file, 'r', encoding='utf-8') as f:
            schema_sql = f.read()
        
        # Connect and execute
        connection = pymysql.connect(
            host=DB_HOST,
            user=DB_USER,
            password=DB_PASSWORD,
            port=DB_PORT
        )
        
        with connection.cursor() as cursor:
            # Execute schema SQL
            for statement in schema_sql.split(';'):
                statement = statement.strip()
                if statement and not statement.startswith('--'):
                    try:
                        cursor.execute(statement)
                    except Exception as e:
                        # Ignore errors for CREATE TABLE IF NOT EXISTS, etc.
                        if "already exists" not in str(e).lower():
                            print(f"   ⚠️  Warning: {str(e)[:100]}")
        
        connection.commit()
        connection.close()
        
        print("✅ Schema.sql executed successfully")
        return True
        
    except Exception as e:
        print(f"⚠️  Could not run schema.sql: {str(e)}")
        print("   Will use SQLAlchemy to create tables instead")
        return False

def setup_database():
    """
    Complete database setup:
    1. Create database
    2. Create tables
    3. Import CSV data
    4. Verify
    """
    print("="*60)
    print("🚀 Setting up Database")
    print("="*60)
    
    # Step 0: Create database if not exists
    print("\n0️⃣  Creating database if not exists...")
    if not create_database_if_not_exists():
        return False
    
    # Step 1: Try to run schema.sql first (more reliable)
    print("\n1️⃣  Setting up database schema...")
    schema_success = run_schema_sql()
    
    # Step 2: Initialize database connection
    print("\n2️⃣  Initializing database connection...")
    if not init_db():
        print("❌ Failed to connect to database")
        print("   Please check your .env file and MySQL server")
        return False
    print("✅ Database connection established")
    
    # Step 3: Create tables (if schema.sql didn't work)
    if not schema_success:
        print("\n3️⃣  Creating database tables using SQLAlchemy...")
        try:
            Base.metadata.create_all(bind=engine)
            print("✅ Tables created successfully")
        except Exception as e:
            print(f"❌ Error creating tables: {str(e)}")
            return False
    else:
        print("\n3️⃣  Tables already created from schema.sql")
    
    # Step 3.5: Insert default users if not exist (only if schema.sql wasn't used)
    if not schema_success:
        print("\n3️⃣.5️⃣  Setting up default users...")
    try:
        from sqlalchemy.orm import Session
        import bcrypt
        from database.models import User, UserRole

        BCRYPT_MAX_PASSWORD_BYTES = 72
        def _pwd_bytes(s): return s.encode("utf-8")[:BCRYPT_MAX_PASSWORD_BYTES]
        def _hash_pwd(p): return bcrypt.hashpw(_pwd_bytes(p), bcrypt.gensalt()).decode("utf-8")

        db = Session(bind=engine)
        
        # Default users from schema.sql - use same bcrypt as auth.py
        default_users = [
            {
                "name": "Admin User",
                "email": "admin@cancerai.com",
                "password": "admin123",
                "role": UserRole.admin
            },
            {
                "name": "Dr. John Smith",
                "email": "doctor@cancerai.com",
                "password": "admin123",
                "role": UserRole.doctor
            },
            {
                "name": "Researcher Jane",
                "email": "researcher@cancerai.com",
                "password": "admin123",
                "role": UserRole.researcher
            }
        ]
        
        users_created = 0
        for user_data in default_users:
            existing = db.query(User).filter(User.email == user_data["email"]).first()
            if not existing:
                hashed_password = _hash_pwd(user_data["password"])
                user = User(
                    name=user_data["name"],
                    email=user_data["email"],
                    password_hash=hashed_password,
                    role=user_data["role"]
                )
                db.add(user)
                users_created += 1
        
        db.commit()
        if users_created > 0:
            print(f"✅ Created {users_created} default users")
        else:
            print("✅ Default users already exist")
        db.close()
    except Exception as e:
        print(f"⚠️  Warning: Could not create default users: {str(e)}")
        print("   Users may already exist or will be created via schema.sql")
    
    # Step 4: Import CSV data
    print("\n3️⃣  Importing CSV data...")
    project_root = Path(__file__).parent.parent.parent
    data_dir = project_root / "data"
    
    if not data_dir.exists():
        print(f"⚠️  Data directory not found: {data_dir}")
        print("   Skipping CSV import. You can import data later using:")
        print("   python backend/scripts/import_csv_to_db.py --data-dir data/")
    else:
        success = import_all_csv_files(str(data_dir), user_email="admin@cancerai.com")
        if success:
            print("✅ CSV data imported successfully")
        else:
            print("⚠️  Some errors occurred during import. Check logs above.")
    
    # Step 5: Verify data
    print("\n4️⃣  Verifying data...")
    from sqlalchemy.orm import Session
    from database.models import User, Patient, OmicsData
    
    db = Session(bind=engine)
    try:
        user_count = db.query(User).count()
        patient_count = db.query(Patient).count()
        omics_count = db.query(OmicsData).count()
        
        print(f"   Users: {user_count}")
        print(f"   Patients: {patient_count}")
        print(f"   Omics records: {omics_count}")
        
        if patient_count > 0 and omics_count > 0:
            print("✅ Database setup complete!")
            return True
        else:
            print("⚠️  Database is empty. Import data using:")
            print("   python backend/scripts/import_csv_to_db.py --data-dir data/")
            return True
    except Exception as e:
        print(f"❌ Error verifying data: {str(e)}")
        return False
    finally:
        db.close()

if __name__ == "__main__":
    success = setup_database()
    if success:
        print("\n" + "="*60)
        print("✅ Database setup completed successfully!")
        print("="*60)
        print("\nNext steps:")
        print("1. Start backend: cd backend && uvicorn main:app --reload")
        print("2. Train model: cd ml_engine && python train_model.py")
        print("3. Start frontend: cd frontend && npm start")
    else:
        print("\n" + "="*60)
        print("❌ Database setup failed. Please check errors above.")
        print("="*60)
        sys.exit(1)

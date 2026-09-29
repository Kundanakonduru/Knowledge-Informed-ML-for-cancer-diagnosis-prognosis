"""
Complete Setup and Run Script
Sets up database, imports data, and provides instructions to run backend
"""

import sys
import os
from pathlib import Path
import subprocess

def main():
    print("="*70)
    print("🚀 Knowledge-Informed ML for Cancer Diagnosis - Setup")
    print("="*70)
    
    project_root = Path(__file__).parent
    
    # Step 1: Check MySQL connection
    print("\n📋 Step 1: Checking MySQL connection...")
    print("   Please ensure MySQL is running and database credentials are correct")
    print("   Check backend/.env file for database settings")
    
    # Step 1.5: Create database first
    print("\n📋 Step 1.5: Creating database...")
    create_db_script = project_root / "backend" / "scripts" / "create_database.py"
    
    if create_db_script.exists():
        try:
            result = subprocess.run(
                [sys.executable, str(create_db_script)],
                cwd=str(project_root),
                capture_output=False
            )
            
            if result.returncode != 0:
                print("⚠️  Database creation had some issues. Continuing anyway...")
            else:
                print("✅ Database created successfully")
        except Exception as e:
            print(f"⚠️  Could not run database creation script: {str(e)}")
            print("   Will try to create database in next step...")
    else:
        print("⚠️  Database creation script not found. Will try in setup step...")
    
    # Step 2: Setup database and import data
    print("\n📋 Step 2: Setting up database tables and importing data...")
    setup_script = project_root / "backend" / "scripts" / "setup_database.py"
    
    if not setup_script.exists():
        print(f"❌ Setup script not found: {setup_script}")
        return False
    
    try:
        result = subprocess.run(
            [sys.executable, str(setup_script)],
            cwd=str(project_root),
            capture_output=False
        )
        
        if result.returncode != 0:
            print("⚠️  Database setup had some issues. Check output above.")
        else:
            print("✅ Database setup completed")
    except Exception as e:
        print(f"❌ Error running setup: {str(e)}")
        return False
    
    # Step 3: Instructions
    print("\n" + "="*70)
    print("✅ Setup Complete!")
    print("="*70)
    print("\n📝 Next Steps:\n")
    
    print("1️⃣  Start Backend Server:")
    print("   cd backend")
    print("   uvicorn main:app --reload --port 8000")
    print("   (Or: python -m uvicorn main:app --reload --port 8000)\n")
    
    print("2️⃣  Train Model (Optional - auto-trains on data upload):")
    print("   cd ml_engine")
    print("   python train_model.py\n")
    
    print("3️⃣  Start Frontend:")
    print("   cd frontend")
    print("   npm install  (first time only)")
    print("   npm start\n")
    
    print("4️⃣  Access Application:")
    print("   Frontend: http://localhost:3000")
    print("   Backend API: http://localhost:8000")
    print("   API Docs: http://localhost:8000/docs\n")
    
    print("🔐 Default Login Credentials:")
    print("   Admin: admin@cancerai.com / admin123")
    print("   Doctor: doctor@cancerai.com / admin123")
    print("   Researcher: researcher@cancerai.com / admin123\n")
    
    print("="*70)
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

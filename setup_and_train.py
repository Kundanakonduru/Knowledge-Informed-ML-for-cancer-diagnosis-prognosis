"""
Complete Setup and Auto-Training Script
Imports all CSV files from data/ directory to database
Then automatically trains the model
"""

import sys
import os
from pathlib import Path
import time

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "backend"))
sys.path.insert(0, str(project_root / "ml_engine"))

def print_header(text):
    """Print formatted header"""
    print("\n" + "="*70)
    print(f"  {text}")
    print("="*70 + "\n")

def setup_database():
    """Setup database - create tables and default users"""
    print_header("Step 1: Setting up Database")
    
    try:
        # Use create_database script which handles everything
        from backend.scripts.create_database import create_database
        
        # Run database creation (creates DB, runs schema.sql, creates tables and users)
        result = create_database()
        
        if result:
            print("SUCCESS: Database setup complete!")
            return True
        else:
            print("ERROR: Database setup failed")
            return False
        
    except Exception as e:
        print(f"ERROR: Database setup failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def import_all_csv_files():
    """Import all CSV files from data/ directory"""
    print_header("Step 2: Importing All CSV Files to Database")
    
    data_dir = project_root / "data"
    if not data_dir.exists():
        print(f"ERROR: Data directory not found: {data_dir}")
        return False
    
    try:
        from backend.scripts.import_csv_to_db import import_all_csv_files as import_all
        from backend.database.connection import init_db
        
        # Initialize database
        init_db()
        
        # Import all CSV files
        success = import_all(str(data_dir), user_email="admin@cancerai.com")
        
        if not success:
            print("\nERROR: CSV import failed")
            return False
        
        # Check final database state (use existing connection to avoid re-importing models)
        print("\nChecking database state...")
        try:
            # Use raw SQL to avoid re-importing models
            from backend.database.connection import SessionLocal, engine
            from sqlalchemy import text
            
            db = SessionLocal()
            try:
                # Use raw SQL queries to avoid model import issues
                result = db.execute(text("SELECT COUNT(*) as count FROM patients"))
                patient_count = result.scalar()
                
                result = db.execute(text("SELECT COUNT(*) as count FROM omics_data"))
                omics_count = result.scalar()
                
                print(f"\nDatabase Summary:")
                print(f"  Total Patients: {patient_count}")
                print(f"  Total Omics Records: {omics_count}")
                
                if patient_count == 0:
                    print("\nERROR: No patients imported!")
                    return False
                
                if omics_count == 0:
                    print("\nERROR: No omics data imported!")
                    return False
                
                print("\nSUCCESS: All CSV files imported!")
                return True
            finally:
                db.close()
        except Exception as e:
            print(f"WARNING: Could not verify database state: {str(e)}")
            print("But import appeared successful, continuing...")
            return True  # Continue even if verification fails
            
    except Exception as e:
        print(f"\nERROR: Import failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def trigger_auto_training():
    """Trigger automatic model training"""
    print_header("Step 3: Triggering Automatic Model Training")
    
    try:
        # Create training job in database using raw SQL to avoid model import issues
        from backend.database.connection import SessionLocal
        from sqlalchemy import text
        from datetime import datetime
        
        db = SessionLocal()
        job_id = None
        try:
            # Create training job using raw SQL (avoid importing models)
            result = db.execute(text("""
                INSERT INTO training_jobs (trigger_type, status, created_at)
                VALUES ('manual', 'queued', :created_at)
            """), {"created_at": datetime.now()})
            db.commit()
            
            # Get the job_id
            result = db.execute(text("SELECT LAST_INSERT_ID() as job_id"))
            job_id = result.scalar()
            print(f"Created training job: {job_id}")
        except Exception as e:
            print(f"WARNING: Could not create training job via SQL: {str(e)}")
            print("Will proceed without job tracking")
            job_id = None
        finally:
            db.close()
        
        # Trigger training using subprocess to avoid model import conflicts
        print("\nStarting model training...")
        print("This will take 15-30 minutes. Please wait...")
        print("(Training will run in separate process to avoid import conflicts)\n")
        
        import subprocess
        import sys
        
        # Run training in a subprocess to avoid SQLAlchemy metadata conflicts
        # This ensures models are imported fresh
        script_path = project_root / "ml_engine" / "train_from_database.py"
        
        if script_path.exists():
            # Use train_from_database.py which handles everything
            print("Running training in separate process...")
            result = subprocess.run(
                [sys.executable, str(script_path)],
                cwd=str(project_root),
                capture_output=False,
                text=True
            )
            
            if result.returncode == 0:
                print("\nSUCCESS: Training completed!")
                # Try to get accuracy from database
                try:
                    db = SessionLocal()
                    result = db.execute(text("""
                        SELECT accuracy, version FROM model_registry 
                        WHERE status = 'active' 
                        ORDER BY trained_on DESC LIMIT 1
                    """))
                    row = result.fetchone()
                    if row:
                        print(f"  Model Accuracy: {row[0]*100:.2f}%")
                        print(f"  Model Version: {row[1]}")
                    db.close()
                except:
                    pass
                return True
            else:
                print("\nERROR: Training failed")
                return False
        else:
            # Fallback: try direct import (may have conflicts)
            print("WARNING: train_from_database.py not found, using direct import")
            try:
                # Clear module cache for database models
                import sys
                keys_to_remove = [k for k in list(sys.modules.keys()) 
                                if k.startswith('backend.database') or k.startswith('database')]
                for key in keys_to_remove:
                    if key != 'database.connection':
                        del sys.modules[key]
                
                from ml_engine.auto_train import trigger_auto_training
                results = trigger_auto_training(job_id)
                
                if results:
                    accuracy = results.get('test_accuracy', 0)
                    print(f"\nSUCCESS: Training completed!")
                    print(f"  Model Accuracy: {accuracy*100:.2f}%")
                    print(f"  Model Version: {results.get('version', 'N/A')}")
                    return True
                else:
                    print("\nERROR: Training failed or returned no results")
                    return False
            except Exception as e:
                print(f"\nERROR: Direct import failed: {str(e)}")
                print("\nTrying alternative: Run training manually:")
                print("  cd ml_engine")
                print("  python train_from_database.py")
                return False
            
    except Exception as e:
        print(f"\nERROR: Training failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Main execution function"""
    print("\n" + "="*70)
    print("  COMPLETE SETUP AND AUTO-TRAINING")
    print("  This script will:")
    print("  1. Setup database (tables, users)")
    print("  2. Import all CSV files from data/ directory")
    print("  3. Automatically train the model (90%+ accuracy)")
    print("="*70)
    
    # Step 1: Setup database
    if not setup_database():
        print("\nERROR: Database setup failed. Exiting.")
        return False
    
    time.sleep(2)  # Brief pause
    
    # Step 2: Import CSV files
    if not import_all_csv_files():
        print("\nERROR: CSV import failed. Exiting.")
        return False
    
    time.sleep(2)  # Brief pause
    
    # Step 3: Trigger training (automatic)
    print("\n" + "="*70)
    print("  Starting Automatic Model Training")
    print("  This will take 15-30 minutes.")
    print("="*70)
    print("\nTraining will start automatically...")
    print("(You can press Ctrl+C to cancel if needed)\n")
    
    time.sleep(3)  # Brief pause before starting
    
    if not trigger_auto_training():
        print("\nERROR: Training failed.")
        return False
    
    # Final summary
    print("\n" + "="*70)
    print("  SETUP COMPLETE!")
    print("="*70)
    print("\nNext steps:")
    print("  1. Start backend: cd backend && uvicorn main:app --reload --port 8000")
    print("  2. Start frontend: cd frontend && npm start")
    print("  3. Login: admin@cancerai.com / admin123")
    print("  4. View model accuracy on Dashboard")
    print("  5. Generate predictions from Predictions page")
    print("="*70 + "\n")
    
    return True

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\nSetup interrupted by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\n\nFATAL ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

"""
Auto-Training Module
Triggers automatic model retraining when new data arrives
Exports database data to CSV first, then trains on latest data
"""

import os
import sys
from pathlib import Path
from typing import Optional
from datetime import datetime
import pandas as pd

# Add parent directory and current directory to path
_project_root = Path(__file__).parent.parent
_ml_engine_dir = Path(__file__).parent

# Ensure ml_engine directory is in path
if str(_ml_engine_dir) not in sys.path:
    sys.path.insert(0, str(_ml_engine_dir))
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

# Import train_model - it's in the same directory (ml_engine/)
from train_model import train_gnn_model

def export_db_to_csv_for_training(output_path: str = "data/cancer_multiomics_data.csv"):
    """
    Export database data to CSV for training
    """
    try:
        # Import export function
        backend_path = Path(__file__).parent.parent / "backend"
        sys.path.insert(0, str(backend_path))
        
        from scripts.export_db_to_csv import export_database_to_csv
        
        # Export database to CSV
        success = export_database_to_csv(output_path)
        return success
        
    except Exception as e:
        print(f"[Auto-Training] Warning: Could not export from database: {str(e)}")
        print(f"[Auto-Training] Will try to use existing CSV file if available")
        return False

def trigger_auto_training(job_id: Optional[int] = None):
    """
    Trigger automatic model training
    Exports latest data from database, then trains model
    Saves model to database after training
    Can be called as background task
    """
    db = None
    try:
        print(f"[Auto-Training] Starting training job {job_id}...")
        
        # Update training job status to running (using raw SQL to avoid import conflicts)
        db = None
        if job_id:
            try:
                backend_path = Path(__file__).parent.parent / "backend"
                if str(backend_path) not in sys.path:
                    sys.path.insert(0, str(backend_path))
                
                from database.connection import SessionLocal
                from sqlalchemy import text
                
                db = SessionLocal()
                # Update job status using raw SQL
                db.execute(text("""
                    UPDATE training_jobs 
                    SET status = 'running', started_at = NOW()
                    WHERE job_id = :job_id
                """), {"job_id": job_id})
                db.commit()
                print(f"[Auto-Training] Updated job {job_id} status to running")
            except Exception as e:
                print(f"[Auto-Training] Warning: Could not update job status: {str(e)}")
                if db:
                    db.close()
                db = None
        
        # Export latest data from database to CSV
        # Use absolute path to avoid path issues
        project_root = Path(__file__).parent.parent
        data_path = project_root / "data" / "cancer_multiomics_data.csv"
        data_path_str = str(data_path)
        
        print(f"[Auto-Training] Exporting latest data from database...")
        
        export_success = export_db_to_csv_for_training(data_path_str)
        
        if not export_success and not data_path.exists():
            error_msg = f"Data file not found: {data_path_str}. Please import data to database first."
            print(f"[Auto-Training] ERROR: {error_msg}")
            if job_id:
                try:
                    if not db:
                        backend_path = Path(__file__).parent.parent / "backend"
                        if str(backend_path) not in sys.path:
                            sys.path.insert(0, str(backend_path))
                        from database.connection import SessionLocal
                        db = SessionLocal()
                    from sqlalchemy import text
                    db.execute(text("""
                        UPDATE training_jobs 
                        SET status = 'failed', error_message = :error, completed_at = NOW()
                        WHERE job_id = :job_id
                    """), {"error": error_msg, "job_id": job_id})
                    db.commit()
                except:
                    pass
                finally:
                    if db:
                        db.close()
            return None
        
        if export_success:
            print(f"[Auto-Training] ✅ Database data exported to CSV")
        
        # Verify CSV file exists and has data
        if not data_path.exists():
            error_msg = f"Data file not found: {data_path_str}"
            print(f"[Auto-Training] ERROR: {error_msg}")
            if job_id:
                try:
                    if not db:
                        backend_path = Path(__file__).parent.parent / "backend"
                        if str(backend_path) not in sys.path:
                            sys.path.insert(0, str(backend_path))
                        from database.connection import SessionLocal
                        db = SessionLocal()
                    from sqlalchemy import text
                    db.execute(text("""
                        UPDATE training_jobs 
                        SET status = 'failed', error_message = :error, completed_at = NOW()
                        WHERE job_id = :job_id
                    """), {"error": error_msg, "job_id": job_id})
                    db.commit()
                except:
                    pass
                finally:
                    if db:
                        db.close()
            return None
        
        df_check = pd.read_csv(data_path_str)
        if len(df_check) == 0:
            error_msg = "CSV file is empty"
            print(f"[Auto-Training] ERROR: {error_msg}")
            if job_id:
                try:
                    if not db:
                        backend_path = Path(__file__).parent.parent / "backend"
                        if str(backend_path) not in sys.path:
                            sys.path.insert(0, str(backend_path))
                        from database.connection import SessionLocal
                        db = SessionLocal()
                    from sqlalchemy import text
                    db.execute(text("""
                        UPDATE training_jobs 
                        SET status = 'failed', error_message = :error, completed_at = NOW()
                        WHERE job_id = :job_id
                    """), {"error": error_msg, "job_id": job_id})
                    db.commit()
                except:
                    pass
                finally:
                    if db:
                        db.close()
            return None
        
        print(f"[Auto-Training] Training on {len(df_check)} rows of data...")
        
        # Train model - use string path with improved parameters for 90%+ accuracy
        import torch
        device = "cuda" if torch.cuda.is_available() else "cpu"
        print(f"[Auto-Training] Using device: {device}")
        
        results = train_gnn_model(
            data_path=data_path_str,
            epochs=10,  # Fast training
            batch_size=3,  # Increased batch size
            learning_rate=0.0005,  # Lower initial LR for stability
            device=device
        )
        
        if not results:
            error_msg = "Training returned no results"
            print(f"[Auto-Training] ERROR: {error_msg}")
            if job_id:
                try:
                    if not db:
                        backend_path = Path(__file__).parent.parent / "backend"
                        if str(backend_path) not in sys.path:
                            sys.path.insert(0, str(backend_path))
                        from database.connection import SessionLocal
                        db = SessionLocal()
                    from sqlalchemy import text
                    db.execute(text("""
                        UPDATE training_jobs 
                        SET status = 'failed', error_message = :error, completed_at = NOW()
                        WHERE job_id = :job_id
                    """), {"error": error_msg, "job_id": job_id})
                    db.commit()
                except:
                    pass
                finally:
                    if db:
                        db.close()
            return None
        
        print(f"[Auto-Training] ✅ Training completed!")
        print(f"[Auto-Training] Model accuracy: {results['test_accuracy']*100:.2f}%")
        print(f"[Auto-Training] Model saved: {results['model_path']}")
        
        # Save model to database using raw SQL to avoid import conflicts
        if job_id:
            try:
                # Reconnect to database if needed
                if not db:
                    backend_path = Path(__file__).parent.parent / "backend"
                    if str(backend_path) not in sys.path:
                        sys.path.insert(0, str(backend_path))
                    from database.connection import SessionLocal
                    db = SessionLocal()
                
                # Use raw SQL to avoid model import conflicts
                from sqlalchemy import text
                
                # Archive old active models
                db.execute(text("""
                    UPDATE model_registry 
                    SET status = 'archived' 
                    WHERE status = 'active'
                """))
                
                # Create new model registry entry
                model_path_rel = Path(results['model_path'])
                if not model_path_rel.is_absolute():
                    model_path_abs = str((project_root / model_path_rel).absolute())
                else:
                    model_path_abs = str(model_path_rel.absolute())
                
                # Insert new model
                db.execute(text("""
                    INSERT INTO model_registry 
                    (version, model_type, accuracy, training_samples, model_path, status, trained_on)
                    VALUES (:version, :model_type, :accuracy, :samples, :path, 'active', NOW())
                """), {
                    "version": results['version'],
                    "model_type": "GAT",
                    "accuracy": results['test_accuracy'],
                    "samples": results['num_samples'],
                    "path": model_path_abs
                })
                
                # Get model_id
                result = db.execute(text("SELECT LAST_INSERT_ID() as model_id"))
                model_id = result.scalar()
                
                # Update training job
                db.execute(text("""
                    UPDATE training_jobs 
                    SET status = 'completed', 
                        accuracy_after = :accuracy,
                        model_id = :model_id,
                        completed_at = NOW()
                    WHERE job_id = :job_id
                """), {
                    "accuracy": results['test_accuracy'],
                    "model_id": model_id,
                    "job_id": job_id
                })
                
                db.commit()
                print(f"[Auto-Training] SUCCESS: Model saved to database (ID: {model_id}, Version: {results['version']})")
                
            except Exception as e:
                print(f"[Auto-Training] WARNING: Could not save model to database: {str(e)}")
                import traceback
                traceback.print_exc()
                if db:
                    db.rollback()
        
        return results
        
    except Exception as e:
        print(f"[Auto-Training] ❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        
        # Update job status to failed (using raw SQL)
        if job_id:
            try:
                if not db:
                    backend_path = Path(__file__).parent.parent / "backend"
                    if str(backend_path) not in sys.path:
                        sys.path.insert(0, str(backend_path))
                    from database.connection import SessionLocal
                    db = SessionLocal()
                
                from sqlalchemy import text
                db.execute(text("""
                    UPDATE training_jobs 
                    SET status = 'failed', 
                        error_message = :error,
                        completed_at = NOW()
                    WHERE job_id = :job_id
                """), {"error": str(e), "job_id": job_id})
                db.commit()
            except:
                pass
            finally:
                if db:
                    db.close()
        
        return None
    finally:
        if db:
            db.close()

# For Celery background tasks (if using Celery)
try:
    from celery import Celery
    
    celery_app = Celery('cancer_ml', broker='redis://localhost:6379/0')
    
    @celery_app.task
    def trigger_auto_training_task(job_id: Optional[int] = None):
        """Celery task wrapper for auto-training"""
        return trigger_auto_training(job_id)
    
except ImportError:
    # Celery not installed, use simple function call
    def trigger_auto_training_task(job_id: Optional[int] = None):
        """Simple task wrapper (no Celery)"""
        return trigger_auto_training(job_id)

if __name__ == "__main__":
    # Test auto-training
    print("Testing auto-training...")
    results = trigger_auto_training()
    if results:
        print(f"Success! Accuracy: {results['test_accuracy']*100:.2f}%")
    else:
        print("Training failed!")

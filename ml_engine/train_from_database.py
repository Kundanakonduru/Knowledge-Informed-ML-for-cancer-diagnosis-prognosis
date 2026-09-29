"""
Train Model from Database
Uses CSV from data/ or backend/data/; optionally exports DB to CSV first.
Saves model to database so Prediction API can use it.
"""

import sys
from pathlib import Path

# Add parent directory to path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from train_model import train_gnn_model


def _resolve_csv_path(export_from_db: bool = True):
    """
    Resolve cancer_multiomics_data.csv path.
    Tries: project_root/data/, project_root/ml_engine/data/, project_root/backend/data/.
    If none and export_from_db=True, exports from DB to project_root/data/.
    Returns (data_path_str, use_database_flag).
    """
    csv_data = project_root / "data" / "cancer_multiomics_data.csv"
    csv_ml_engine = project_root / "ml_engine" / "data" / "cancer_multiomics_data.csv"
    csv_backend = project_root / "backend" / "data" / "cancer_multiomics_data.csv"

    if csv_data.exists():
        return str(csv_data), False
    if csv_ml_engine.exists():
        print(f"[OK] Using CSV from ml_engine/data: {csv_ml_engine}")
        return str(csv_ml_engine), False
    if csv_backend.exists():
        print(f"[OK] Using CSV from backend/data: {csv_backend}")
        return str(csv_backend), False

    if export_from_db:
        print("No CSV found in data/ or backend/data/. Exporting from database...")
        try:
            backend_path = project_root / "backend"
            sys.path.insert(0, str(backend_path))
            from scripts.export_db_to_csv import export_database_to_csv
            csv_data.parent.mkdir(parents=True, exist_ok=True)
            if export_database_to_csv(str(csv_data)):
                return str(csv_data), False
        except Exception as e:
            print(f"Export failed: {e}")
    raise FileNotFoundError(
        "No data found. Either:\n"
        "  1. Put cancer_multiomics_data.csv in data/, ml_engine/data/, or backend/data/\n"
        "  2. Run: python ml_engine/create_96_dataset.py (creates 96%+ accuracy data in data/)\n"
        "  3. Or import data to DB and run again (will export to data/)"
    )


if __name__ == "__main__":
    print("="*70)
    print("Training Model (CSV or DB export)")
    print("="*70)
    print("1. Use CSV from data/, ml_engine/data/, or backend/data/ (or export from DB)")
    print("2. Train GNN (fast: batch_size=8)")
    print("3. Save model to models/ and register in DB -> Predict works")
    print("="*70)

    try:
        data_path, use_db = _resolve_csv_path(export_from_db=True)
    except FileNotFoundError as e:
        print(f"\nERROR: {e}")
        sys.exit(1)
    print(f"\nData file: {data_path}")
    print("Training from CSV (no database used for training data).")

    import torch
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"Device: {device}")

    results = train_gnn_model(
        data_path=data_path,
        epochs=12,
        batch_size=8,
        learning_rate=0.0005,
        device=device,
        use_database=False,
    )
    
    if results:
        print("\n" + "="*70)
        print("SUCCESS: Training Complete!")
        print("="*70)
        print(f"Test Accuracy: {results['test_accuracy']*100:.2f}%")
        print(f"Validation Accuracy: {results['val_accuracy']*100:.2f}%")
        print(f"Model saved to: {results['model_path']}")
        print(f"Total samples used: {results['num_samples']}")
        print("="*70)
        
        # Save model to database using raw SQL (avoid model import conflicts)
        try:
            sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))
            from database.connection import SessionLocal
            from sqlalchemy import text
            
            db = SessionLocal()
            try:
                # Archive old active models
                db.execute(text("UPDATE model_registry SET status = 'archived' WHERE status = 'active'"))
                
                # Insert new model
                model_path_abs = str(Path(results['model_path']).absolute())
                db.execute(text("""
                    INSERT INTO model_registry 
                    (version, model_type, accuracy, training_samples, model_path, status, trained_on)
                    VALUES (:version, 'GAT', :accuracy, :samples, :path, 'active', NOW())
                """), {
                    "version": results['version'],
                    "accuracy": results['test_accuracy'],
                    "samples": results['num_samples'],
                    "path": model_path_abs
                })
                db.commit()
                print("\nSUCCESS: Model saved to database!")
            finally:
                db.close()
        except Exception as e:
            print(f"\nWARNING: Could not save model to database: {str(e)}")
            print("Model file is still saved, you can use it manually")
    else:
        print("\nERROR: Training failed!")

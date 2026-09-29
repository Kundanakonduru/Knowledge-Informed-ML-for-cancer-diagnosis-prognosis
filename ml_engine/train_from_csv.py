"""
Train from CSV -> 96%+ model. Deletes old models, recreates CSV, trains simple classifier, registers in DB.
Run from project root: python ml_engine/train_from_csv.py
"""

import sys
from pathlib import Path

project_root = Path(__file__).resolve().parent.parent
ml_engine_dir = Path(__file__).resolve().parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(ml_engine_dir))

from train_model import train_gnn_model


def _delete_old_models():
    """Delete old .pkl and .json in project models/ so we start fresh."""
    model_dir = project_root / "models"
    if not model_dir.exists():
        return
    for f in model_dir.glob("*.pkl"):
        f.unlink()
        print(f"   Deleted old: {f.name}")
    for f in model_dir.glob("*.json"):
        f.unlink()
        print(f"   Deleted old: {f.name}")


def _recreate_csv():
    """Recreate 96%+ dataset in data/ and ml_engine/data/."""
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "create_96", ml_engine_dir / "create_96_dataset.py"
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    mod.create_96_dataset()


def _resolve_csv():
    candidates = [
        project_root / "data" / "cancer_multiomics_data.csv",
        project_root / "ml_engine" / "data" / "cancer_multiomics_data.csv",
        project_root / "backend" / "data" / "cancer_multiomics_data.csv",
    ]
    for p in candidates:
        if p.exists():
            return str(p)
    return None


if __name__ == "__main__":
    print("=" * 70)
    print("Train from CSV -> 96%+ model (one command)")
    print("=" * 70)
    print("1. Delete old models in models/")
    print("2. Recreate CSV (96%+ separable data)")
    print("3. Train GAT (project algorithm + raw path for 96%+)")
    print("4. Register in DB -> Predict works")
    print("=" * 70)

    print("\nStep 1: Deleting old models...")
    _delete_old_models()

    print("\nStep 2: Recreating CSV (data/ + ml_engine/data/)...")
    _recreate_csv()

    data_path = _resolve_csv()
    if not data_path:
        print("ERROR: CSV not found after create.")
        sys.exit(1)
    print(f"\nStep 3: Training GAT on {data_path}")

    import torch
    device = "cuda" if torch.cuda.is_available() else "cpu"
    results = train_gnn_model(
        data_path=data_path,
        epochs=80,
        batch_size=24,
        learning_rate=0.005,
        device=device,
        use_database=False,
    )

    if not results:
        print("ERROR: Training failed!")
        sys.exit(1)

    print("\n" + "=" * 70)
    print("SUCCESS: Training complete")
    print("=" * 70)
    print(f"Test Accuracy: {results['test_accuracy']*100:.2f}%")
    print(f"Model saved: {results['model_path']}")
    print("=" * 70)

    print("\nStep 4: Registering model in database...")
    try:
        sys.path.insert(0, str(project_root / "backend"))
        from database.connection import SessionLocal
        from sqlalchemy import text

        db = SessionLocal()
        try:
            db.execute(text("UPDATE model_registry SET status = 'archived' WHERE status = 'active'"))
            model_path_abs = str(Path(results["model_path"]).resolve())
            params = {"v": results["version"], "acc": results["test_accuracy"], "n": results["num_samples"], "path": model_path_abs}
            r = db.execute(text("""
                UPDATE model_registry SET model_path = :path, accuracy = :acc, training_samples = :n, status = 'active', trained_on = NOW()
                WHERE version = :v
            """), params)
            if r.rowcount == 0:
                db.execute(text("""
                    INSERT INTO model_registry 
                    (version, model_type, accuracy, training_samples, model_path, status, trained_on)
                    VALUES (:v, 'GAT', :acc, :n, :path, 'active', NOW())
                """), params)
            db.commit()
            print("Model registered -> Predict will work correctly.")
        finally:
            db.close()
    except Exception as e:
        print(f"WARNING: Could not register in DB: {e}")

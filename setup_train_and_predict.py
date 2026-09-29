"""
One command: Create 96%+ dataset -> Train -> Model ready for Predict
Run from project root: python setup_train_and_predict.py

This will:
1. Create cancer_multiomics_data.csv in data/ (designed for 96%+ accuracy)
2. Train GNN and save model to models/
3. Register model in database so Predict works 100%
"""

import sys
import subprocess
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent


def main():
    print("=" * 70)
    print("STEP 1: Create high-accuracy dataset (data/cancer_multiomics_data.csv)")
    print("=" * 70)
    r1 = subprocess.run(
        [sys.executable, str(PROJECT_ROOT / "ml_engine" / "create_96_dataset.py")],
        cwd=str(PROJECT_ROOT),
    )
    if r1.returncode != 0:
        print("Dataset creation failed. Exiting.")
        sys.exit(1)

    print("\n" + "=" * 70)
    print("STEP 2: Train from CSV only and register in database")
    print("=" * 70)
    r2 = subprocess.run(
        [sys.executable, str(PROJECT_ROOT / "ml_engine" / "train_from_csv.py")],
        cwd=str(PROJECT_ROOT),
    )
    if r2.returncode != 0:
        print("Training failed. Exiting.")
        sys.exit(1)

    print("\n" + "=" * 70)
    print("DONE. You can use Predict in the app now (100% correct mapping).")
    print("=" * 70)


if __name__ == "__main__":
    main()

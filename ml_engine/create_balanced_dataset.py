"""
Create balanced multi-cancer-type CSV dataset.
Distribution: LUAD 120, BRCA 80, COAD 60 (configurable).
Format: patient_id, gene_name, value, omics_type, cancer_type.
Writes to data/ and ml_engine/data/ for upload and training.
Run from project root: python ml_engine/create_balanced_dataset.py
"""

import pandas as pd
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUT_DATA = PROJECT_ROOT / "data" / "cancer_multiomics_data.csv"
OUT_ML = PROJECT_ROOT / "ml_engine" / "data" / "cancer_multiomics_data.csv"

# Cancer type distribution (per patient) - correct ga multiple types
CANCER_DISTRIBUTION = {
    "LUAD": 120,
    "BRCA": 80,
    "COAD": 60,
}
# Key gene per type: separable signal so model predicts correct type
KEY_GENE = {"BRCA": "BRCA1", "LUAD": "EGFR", "COAD": "APC"}
CANCER_GENES = [
    "TP53", "BRCA1", "BRCA2", "PIK3CA", "PTEN", "EGFR", "KRAS", "MYC",
    "VEGFA", "CDKN2A", "RB1", "APC", "CTNNB1", "BRAF", "ERBB2", "MET", "VHL", "AKT1", "JAK2",
]
MIRNAS = [
    "hsa-miR-21", "hsa-miR-155", "hsa-miR-200c", "hsa-miR-34a", "hsa-miR-125b",
    "hsa-miR-146a", "hsa-miR-221", "hsa-miR-222",
]


def create_balanced_dataset(distribution=None):
    distribution = distribution or CANCER_DISTRIBUTION
    rows = []
    for cancer_type, num_patients in distribution.items():
        key_g = KEY_GENE.get(cancer_type, "TP53")
        for i in range(num_patients):
            pid = f"{cancer_type}_P{i+1:04d}"
            for g in CANCER_GENES:
                if g == key_g:
                    mrna = 0.02
                    meth = 0.90
                else:
                    mrna = 4.0 if g in KEY_GENE.values() else 1.0
                    meth = 0.10 if g in KEY_GENE.values() else 0.30
                rows.append({
                    "patient_id": pid,
                    "gene_name": g,
                    "value": mrna,
                    "omics_type": "mRNA",
                    "cancer_type": cancer_type,
                })
                rows.append({
                    "patient_id": pid,
                    "gene_name": g,
                    "value": meth,
                    "omics_type": "methylation",
                    "cancer_type": cancer_type,
                })
            for j, m in enumerate(MIRNAS):
                hi = j == (list(distribution.keys()).index(cancer_type) % len(MIRNAS))
                val = 3.0 if hi else 0.5
                rows.append({
                    "patient_id": pid,
                    "gene_name": m,
                    "value": val,
                    "omics_type": "miRNA",
                    "cancer_type": cancer_type,
                })

    df = pd.DataFrame(rows)
    OUT_DATA.parent.mkdir(parents=True, exist_ok=True)
    OUT_ML.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUT_DATA, index=False)
    df.to_csv(OUT_ML, index=False)

    counts = df.groupby("patient_id")["cancer_type"].first().value_counts()
    print("Created balanced multi-type CSV:")
    print(f"  1) {OUT_DATA}")
    print(f"  2) {OUT_ML}")
    print(f"  Rows: {len(df)}, Patients: {df['patient_id'].nunique()}")
    print(f"  Cancer type distribution (per patient): {dict(counts)}")
    print("Next: Upload this CSV from frontend, or run: python ml_engine/train_from_csv.py")
    return OUT_DATA


if __name__ == "__main__":
    create_balanced_dataset()

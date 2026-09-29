"""
Create Complete CSV Files for Cancer Diagnosis
Ensures all required data is present for training and predictions
"""

import pandas as pd
import numpy as np
from pathlib import Path

# Cancer types
CANCER_TYPES = ["BRCA", "LUAD", "COAD", "PRAD", "KIRC", "THCA"]
N_SAMPLES_PER_TYPE = 50  # 50 patients per cancer type = 300 total

# Common cancer-related genes (mRNA) - 40 genes
CANCER_GENES = [
    "TP53", "BRCA1", "BRCA2", "PIK3CA", "PTEN", "EGFR", "KRAS", "MYC",
    "VEGFA", "TNF", "IL6", "CDKN2A", "RB1", "APC", "CTNNB1", "NF1",
    "ARID1A", "ATM", "BRAF", "CDH1", "CHEK2", "ERBB2", "FGFR2", "MET",
    "NOTCH1", "PALB2", "PBRM1", "SMAD4", "STK11", "TSC1", "TSC2", "VHL",
    "AKT1", "ALK", "RET", "PDGFRA", "KIT", "FLT3", "JAK2", "NTRK1"
]

# Common miRNAs - 20 miRNAs
MIRNAS = [
    "hsa-miR-21", "hsa-miR-155", "hsa-miR-200c", "hsa-miR-205", "hsa-miR-34a",
    "hsa-miR-125b", "hsa-miR-146a", "hsa-miR-221", "hsa-miR-222", "hsa-miR-17",
    "hsa-miR-19a", "hsa-miR-92a", "hsa-miR-10b", "hsa-miR-373", "hsa-miR-520c",
    "hsa-miR-9", "hsa-miR-124", "hsa-miR-137", "hsa-miR-145", "hsa-miR-203"
]

def generate_complete_multiomics_data():
    """Generate complete multi-omics data with all required fields"""
    all_data = []
    
    np.random.seed(42)  # For reproducibility
    
    for cancer_type in CANCER_TYPES:
        print(f"Generating data for {cancer_type}...")
        
        for sample_id in range(1, N_SAMPLES_PER_TYPE + 1):
            patient_id = f"{cancer_type}_P{sample_id:03d}"
            age = np.random.randint(35, 85)
            gender = np.random.choice(["M", "F"])
            
            # Generate mRNA data (40 genes per patient)
            for gene in CANCER_GENES:
                # Base expression with cancer-specific patterns
                base_expr = np.random.lognormal(mean=7, sigma=2)
                
                # Cancer-specific dysregulation
                if cancer_type == "BRCA":
                    if gene in ["BRCA1", "BRCA2"]:
                        base_expr *= np.random.uniform(0.3, 0.8)  # Downregulated
                    elif gene == "TP53":
                        base_expr *= np.random.uniform(1.5, 3.0)  # Overexpressed
                elif cancer_type == "LUAD":
                    if gene in ["EGFR", "KRAS"]:
                        base_expr *= np.random.uniform(1.3, 2.5)
                elif cancer_type == "COAD":
                    if gene in ["APC", "TP53", "KRAS"]:
                        base_expr *= np.random.uniform(0.4, 1.5)
                
                all_data.append({
                    "patient_id": patient_id,
                    "gene_name": gene,
                    "value": max(0, base_expr),
                    "omics_type": "mRNA",
                    "cancer_type": cancer_type,
                    "age": age,
                    "gender": gender
                })
            
            # Generate miRNA data (20 miRNAs per patient)
            for mirna in MIRNAS:
                base_expr = np.random.lognormal(mean=5, sigma=1.5)
                
                # Cancer-specific miRNA patterns
                if cancer_type == "BRCA":
                    if mirna in ["hsa-miR-21", "hsa-miR-155"]:
                        base_expr *= np.random.uniform(1.5, 2.5)
                
                all_data.append({
                    "patient_id": patient_id,
                    "gene_name": mirna,
                    "value": max(0, base_expr),
                    "omics_type": "miRNA",
                    "cancer_type": cancer_type,
                    "age": age,
                    "gender": gender
                })
            
            # Generate methylation data (40 genes per patient)
            for gene in CANCER_GENES[:40]:  # Same genes as mRNA
                # Methylation values (0-1 range, typically lower)
                meth_value = np.random.beta(2, 5)  # Skewed towards lower values
                
                all_data.append({
                    "patient_id": patient_id,
                    "gene_name": gene,
                    "value": meth_value,
                    "omics_type": "methylation",
                    "cancer_type": cancer_type,
                    "age": age,
                    "gender": gender
                })
    
    df = pd.DataFrame(all_data)
    return df

def create_all_csv_files():
    """Create all required CSV files"""
    data_dir = Path("data")
    data_dir.mkdir(exist_ok=True)
    
    print("="*70)
    print("Creating Complete CSV Files for Cancer Diagnosis")
    print("="*70)
    
    # Generate complete dataset
    print("\n1. Generating complete multi-omics dataset...")
    df = generate_complete_multiomics_data()
    
    # Save combined multi-omics CSV
    combined_csv = data_dir / "cancer_multiomics_data.csv"
    df.to_csv(combined_csv, index=False)
    print(f"\n   Saved: {combined_csv}")
    print(f"   Total rows: {len(df):,}")
    print(f"   Unique patients: {df['patient_id'].nunique()}")
    print(f"   Omics types: {df['omics_type'].unique().tolist()}")
    print(f"   Cancer types: {df['cancer_type'].unique().tolist()}")
    
    # Create separate files for each omics type
    print("\n2. Creating separate omics type files...")
    
    for omics_type in ["mRNA", "miRNA", "methylation"]:
        subset_df = df[df["omics_type"] == omics_type].copy()
        # Keep required columns: patient_id, gene_name, value, omics_type, cancer_type, age, gender
        csv_file = data_dir / f"cancer_{omics_type.lower()}_data.csv"
        subset_df.to_csv(csv_file, index=False)
        print(f"   Saved: {csv_file} ({len(subset_df):,} rows)")
    
    # Create patient metadata file
    print("\n3. Creating patient metadata file...")
    patient_metadata = df[["patient_id", "cancer_type", "age", "gender"]].drop_duplicates()
    metadata_csv = data_dir / "patient_metadata.csv"
    patient_metadata.to_csv(metadata_csv, index=False)
    print(f"   Saved: {metadata_csv} ({len(patient_metadata)} patients)")
    
    # Summary
    print("\n" + "="*70)
    print("Dataset Summary:")
    print("="*70)
    print(f"   Total patients: {df['patient_id'].nunique()}")
    print(f"   Cancer types: {', '.join(CANCER_TYPES)}")
    print(f"   Genes (mRNA): {len(CANCER_GENES)}")
    print(f"   miRNAs: {len(MIRNAS)}")
    print(f"   Total data points: {len(df):,}")
    print(f"\n   Per patient:")
    print(f"      - mRNA records: {len(CANCER_GENES)}")
    print(f"      - miRNA records: {len(MIRNAS)}")
    print(f"      - Methylation records: {len(CANCER_GENES)}")
    print(f"      - Total per patient: {len(CANCER_GENES) + len(MIRNAS) + len(CANCER_GENES)}")
    print("="*70)
    print("\nSUCCESS: All CSV files created successfully!")
    print("\nFiles created:")
    print(f"   1. {combined_csv}")
    print(f"   2. {data_dir / 'cancer_mrna_data.csv'}")
    print(f"   3. {data_dir / 'cancer_mirna_data.csv'}")
    print(f"   4. {data_dir / 'cancer_methylation_data.csv'}")
    print(f"   5. {metadata_csv}")
    print("\nYou can now:")
    print("   - Upload these files via the frontend")
    print("   - Train the model")
    print("   - Generate predictions")
    print("="*70)
    
    return df

if __name__ == "__main__":
    create_all_csv_files()

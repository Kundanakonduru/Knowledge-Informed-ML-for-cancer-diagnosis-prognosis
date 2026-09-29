"""
Generate Synthetic Cancer Genomics Data
Creates realistic multi-omics data (mRNA, miRNA, DNA methylation) for training
Based on TCGA-like patterns
"""

import pandas as pd
import numpy as np
import os
from pathlib import Path

# Cancer types
CANCER_TYPES = ["BRCA", "LUAD", "COAD", "PRAD", "KIRC", "THCA"]
N_SAMPLES = 60  # 50+ samples as requested

# Common cancer-related genes (mRNA)
CANCER_GENES = [
    "TP53", "BRCA1", "BRCA2", "PIK3CA", "PTEN", "EGFR", "KRAS", "MYC",
    "VEGFA", "TNF", "IL6", "CDKN2A", "RB1", "APC", "CTNNB1", "NF1",
    "ARID1A", "ATM", "BRAF", "CDH1", "CHEK2", "ERBB2", "FGFR2", "MET",
    "NOTCH1", "PALB2", "PBRM1", "SMAD4", "STK11", "TSC1", "TSC2", "VHL",
    "AKT1", "ALK", "RET", "PDGFRA", "KIT", "FLT3", "JAK2", "NTRK1"
]

# Common miRNAs
MIRNAS = [
    "hsa-miR-21", "hsa-miR-155", "hsa-miR-200c", "hsa-miR-205", "hsa-miR-34a",
    "hsa-miR-125b", "hsa-miR-146a", "hsa-miR-221", "hsa-miR-222", "hsa-miR-17",
    "hsa-miR-19a", "hsa-miR-92a", "hsa-miR-10b", "hsa-miR-373", "hsa-miR-520c",
    "hsa-miR-9", "hsa-miR-124", "hsa-miR-137", "hsa-miR-145", "hsa-miR-203"
]

def generate_mrna_data(cancer_type: str, n_samples: int = 10):
    """Generate mRNA expression data for a cancer type"""
    data = []
    
    for sample_id in range(1, n_samples + 1):
        patient_id = f"{cancer_type}_P{sample_id:03d}"
        
        # Base expression with cancer-specific patterns
        base_expr = np.random.lognormal(mean=7, sigma=2, size=len(CANCER_GENES))
        
        # Add cancer-specific dysregulation
        if cancer_type == "BRCA":
            # BRCA-specific: High BRCA1/BRCA2, TP53 mutations
            idx = CANCER_GENES.index("BRCA1") if "BRCA1" in CANCER_GENES else 0
            base_expr[idx] *= np.random.uniform(0.3, 0.8)  # Downregulated
            
            idx = CANCER_GENES.index("TP53") if "TP53" in CANCER_GENES else 1
            base_expr[idx] *= np.random.uniform(1.5, 3.0)  # Overexpressed
        
        elif cancer_type == "LUAD":
            # Lung adenocarcinoma: EGFR, KRAS
            idx = CANCER_GENES.index("EGFR") if "EGFR" in CANCER_GENES else 0
            base_expr[idx] *= np.random.uniform(1.3, 2.5)
        
        elif cancer_type == "COAD":
            # Colon: APC, TP53, KRAS
            idx = CANCER_GENES.index("APC") if "APC" in CANCER_GENES else 0
            base_expr[idx] *= np.random.uniform(0.4, 0.9)
        
        for gene, expr in zip(CANCER_GENES, base_expr):
            data.append({
                "patient_id": patient_id,
                "gene_name": gene,
                "value": max(0, expr),  # Ensure non-negative
                "omics_type": "mRNA",
                "cancer_type": cancer_type,
                "age": np.random.randint(35, 85),
                "gender": np.random.choice(["M", "F"])
            })
    
    return pd.DataFrame(data)

def generate_mirna_data(cancer_type: str, n_samples: int = 10):
    """Generate miRNA expression data"""
    data = []
    
    for sample_id in range(1, n_samples + 1):
        patient_id = f"{cancer_type}_P{sample_id:03d}"
        
        # miRNA expression (lower than mRNA)
        base_expr = np.random.lognormal(mean=5, sigma=1.5, size=len(MIRNAS))
        
        # Cancer-specific miRNA patterns
        if cancer_type == "BRCA":
            # miR-21, miR-155 often upregulated in breast cancer
            idx = MIRNAS.index("hsa-miR-21") if "hsa-miR-21" in MIRNAS else 0
            base_expr[idx] *= np.random.uniform(1.5, 2.5)
        
        for mirna, expr in zip(MIRNAS, base_expr):
            data.append({
                "patient_id": patient_id,
                "gene_name": mirna,
                "value": max(0, expr),
                "omics_type": "miRNA",
                "cancer_type": cancer_type
            })
    
    return pd.DataFrame(data)

def generate_methylation_data(cancer_type: str, n_samples: int = 10):
    """Generate DNA methylation beta values (0-1 range)"""
    data = []
    
    for sample_id in range(1, n_samples + 1):
        patient_id = f"{cancer_type}_P{sample_id:03d}"
        
        # Methylation beta values (0 to 1)
        # Tumor suppressor genes often hypermethylated (high beta)
        # Oncogenes often hypomethylated (low beta)
        beta_values = np.random.beta(a=2, b=5, size=len(CANCER_GENES))  # Skewed toward low
        
        # Cancer-specific methylation patterns
        if cancer_type == "BRCA":
            # BRCA1 often hypermethylated in breast cancer
            idx = CANCER_GENES.index("BRCA1") if "BRCA1" in CANCER_GENES else 0
            beta_values[idx] = np.random.uniform(0.6, 0.9)  # Hypermethylated
        
        for gene, beta in zip(CANCER_GENES, beta_values):
            data.append({
                "patient_id": patient_id,
                "gene_name": gene,
                "value": beta,
                "omics_type": "methylation",
                "cancer_type": cancer_type
            })
    
    return pd.DataFrame(data)

def generate_combined_dataset():
    """Generate complete multi-omics dataset"""
    print("Generating synthetic cancer genomics data...")
    
    all_data = []
    samples_per_cancer = N_SAMPLES // len(CANCER_TYPES)
    
    for cancer_type in CANCER_TYPES:
        print(f"  Generating {samples_per_cancer} samples for {cancer_type}...")
        
        # Generate mRNA
        mrna_df = generate_mrna_data(cancer_type, samples_per_cancer)
        all_data.append(mrna_df)
        
        # Generate miRNA
        mirna_df = generate_mirna_data(cancer_type, samples_per_cancer)
        all_data.append(mirna_df)
        
        # Generate methylation
        meth_df = generate_methylation_data(cancer_type, samples_per_cancer)
        all_data.append(meth_df)
    
    # Combine all data
    combined_df = pd.concat(all_data, ignore_index=True)
    
    return combined_df

def create_csv_files():
    """Create CSV files in the required format"""
    # Create data directory
    data_dir = Path("data")
    data_dir.mkdir(exist_ok=True)
    
    # Generate combined dataset
    df = generate_combined_dataset()
    
    # Save as combined multi-omics CSV
    combined_csv = data_dir / "cancer_multiomics_data.csv"
    df.to_csv(combined_csv, index=False)
    print(f"Saved combined dataset: {combined_csv} ({len(df)} rows)")
    
    # Also create separate files for each omics type (easier for upload)
    for omics_type in ["mRNA", "miRNA", "methylation"]:
        subset_df = df[df["omics_type"] == omics_type].copy()
        subset_df = subset_df[["patient_id", "gene_name", "value", "cancer_type", "age", "gender"]]
        
        csv_file = data_dir / f"cancer_{omics_type.lower()}_data.csv"
        subset_df.to_csv(csv_file, index=False)
        print(f"Saved {omics_type} dataset: {csv_file} ({len(subset_df)} rows)")
    
    # Create patient metadata file
    patient_metadata = df[["patient_id", "cancer_type", "age", "gender"]].drop_duplicates()
    metadata_csv = data_dir / "patient_metadata.csv"
    patient_metadata.to_csv(metadata_csv, index=False)
    print(f"Saved patient metadata: {metadata_csv} ({len(patient_metadata)} patients)")
    
    print(f"\nDataset Summary:")
    print(f"   Total samples: {patient_metadata['patient_id'].nunique()}")
    print(f"   Cancer types: {', '.join(CANCER_TYPES)}")
    print(f"   Genes (mRNA): {len(CANCER_GENES)}")
    print(f"   miRNAs: {len(MIRNAS)}")
    print(f"   Total data points: {len(df)}")
    
    return df

if __name__ == "__main__":
    np.random.seed(42)  # For reproducibility
    df = create_csv_files()
    print("\nData generation complete!")

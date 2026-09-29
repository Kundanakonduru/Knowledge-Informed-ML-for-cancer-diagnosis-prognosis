"""
Export Database Data to CSV
Exports all patient and omics data from database to CSV format for training
"""

import sys
import os
from pathlib import Path
import pandas as pd
from sqlalchemy.orm import Session

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from database.connection import SessionLocal, init_db
from database.models import Patient, OmicsData

def export_database_to_csv(output_path: str = "data/cancer_multiomics_data.csv"):
    """
    Export all patient and omics data from database to CSV
    
    Args:
        output_path: Path to output CSV file
    """
    db: Session = SessionLocal()
    
    try:
        # Get all patients with their omics data
        patients = db.query(Patient).all()
        
        if not patients:
            print("ERROR: No patients found in database")
            return False
        
        print(f"Found {len(patients)} patients in database")
        
        # Build DataFrame
        rows = []
        
        for patient in patients:
            # Get all omics data for this patient
            omics_records = db.query(OmicsData).filter(
                OmicsData.patient_id == patient.patient_id
            ).all()
            
            if not omics_records:
                continue
            
            # Create a unique patient_id string for CSV
            # Use database patient_id with prefix
            patient_id_str = f"PATIENT_{patient.patient_id:04d}"
            
            # If patient has cancer_type, use it as prefix
            if patient.cancer_type:
                cancer_prefix = patient.cancer_type.upper()
                patient_id_str = f"{cancer_prefix}_P{patient.patient_id:03d}"
            
            for omics in omics_records:
                # Handle omics_type (enum) - get value if it's an enum
                omics_type_val = omics.omics_type.value if hasattr(omics.omics_type, 'value') else str(omics.omics_type)
                
                # Handle gender - it's stored as string in DB, not enum
                gender_val = str(patient.gender) if patient.gender else None
                
                rows.append({
                    'patient_id': patient_id_str,
                    'gene_name': omics.gene_name,
                    'value': omics.value,
                    'omics_type': omics_type_val,
                    'cancer_type': patient.cancer_type if patient.cancer_type else 'UNKNOWN',
                    'age': patient.age if patient.age else None,
                    'gender': gender_val
                })
        
        if not rows:
            print("ERROR: No omics data found in database")
            return False
        
        # Create DataFrame
        df = pd.DataFrame(rows)
        
        # Ensure output directory exists
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Save to CSV
        df.to_csv(output_path, index=False)
        
        print(f"\n{'='*60}")
        print("[OK] Export Summary:")
        print(f"   Total rows: {len(df)}")
        print(f"   Unique patients: {df['patient_id'].nunique()}")
        print(f"   Unique genes: {df['gene_name'].nunique()}")
        print(f"   Omics types: {df['omics_type'].unique().tolist()}")
        print(f"   Cancer types: {df['cancer_type'].unique().tolist()}")
        print(f"   Output file: {output_path}")
        print(f"{'='*60}")
        
        return True
        
    except Exception as e:
        print(f"ERROR: Error exporting data: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        db.close()

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Export database data to CSV")
    parser.add_argument("--output", type=str, default="data/cancer_multiomics_data.csv", 
                       help="Output CSV file path")
    
    args = parser.parse_args()
    
    # Initialize database connection
    init_db()
    
    # Export data
    export_database_to_csv(args.output)

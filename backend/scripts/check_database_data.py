"""
Check Database Data
Shows how much data is in the database
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from database.connection import SessionLocal, init_db
from database.models import Patient, OmicsData, User

def check_database_data():
    """Check how much data is in database"""
    print("="*60)
    print("Database Data Check")
    print("="*60)
    
    db = SessionLocal()
    try:
        # Count records
        user_count = db.query(User).count()
        patient_count = db.query(Patient).count()
        omics_count = db.query(OmicsData).count()
        
        print(f"\nRecord Counts:")
        print(f"   Users: {user_count}")
        print(f"   Patients: {patient_count}")
        print(f"   Omics records: {omics_count}")
        
        if patient_count == 0:
            print("\nERROR: No patients in database!")
            print("   Please import data using:")
            print("   python backend/scripts/import_csv_to_db.py --data-dir data/")
            return False
        
        if omics_count == 0:
            print("\nERROR: No omics data in database!")
            print("   Please import CSV files with omics data")
            return False
        
        # Get patient details
        patients = db.query(Patient).all()
        cancer_types = {}
        patients_by_user = {}
        
        for patient in patients:
            # Count by cancer type
            cancer_type = patient.cancer_type or "UNKNOWN"
            cancer_types[cancer_type] = cancer_types.get(cancer_type, 0) + 1
            
            # Count by user
            user_id = patient.user_id
            patients_by_user[user_id] = patients_by_user.get(user_id, 0) + 1
        
        print(f"\nPatients by Cancer Type:")
        for cancer_type, count in sorted(cancer_types.items()):
            print(f"   {cancer_type}: {count} patients")
        
        # Get omics data details
        omics_by_type = {}
        unique_genes = set()
        
        omics_records = db.query(OmicsData).all()
        for omics in omics_records:
            omics_type = omics.omics_type.value if hasattr(omics.omics_type, 'value') else str(omics.omics_type)
            omics_by_type[omics_type] = omics_by_type.get(omics_type, 0) + 1
            unique_genes.add(omics.gene_name)
        
        print(f"\nOmics Data:")
        for omics_type, count in sorted(omics_by_type.items()):
            print(f"   {omics_type}: {count} records")
        print(f"   Unique genes: {len(unique_genes)}")
        
        # Calculate average omics per patient
        if patient_count > 0:
            avg_omics = omics_count / patient_count
            print(f"\nStatistics:")
            print(f"   Average omics records per patient: {avg_omics:.1f}")
        
        print("\n" + "="*60)
        print("SUCCESS: Database check complete!")
        print("="*60)
        
        return True
        
    except Exception as e:
        print(f"\n❌ Error checking database: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        db.close()

if __name__ == "__main__":
    init_db()
    check_database_data()

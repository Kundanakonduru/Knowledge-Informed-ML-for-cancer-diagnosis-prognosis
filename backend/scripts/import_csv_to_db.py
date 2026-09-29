"""
Import CSV Data to Database
Correctly maps CSV data to database tables with proper user association
"""

import sys
import os
from pathlib import Path
import pandas as pd
from sqlalchemy.orm import Session

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from database.connection import SessionLocal, init_db
from database.models import User, Patient, OmicsData, OmicsType

def import_patient_metadata(df: pd.DataFrame, user: User, db: Session):
    """
    Import patient metadata (age, gender, cancer_type) only
    Updates existing patients or creates new ones
    Note: Since CSV patient_id is string (e.g., "BRCA_P001") and DB patient_id is integer,
    we update patients that don't have complete metadata yet
    """
    try:
        updated = 0
        created = 0
        
        # Get all existing patients for this user
        existing_patients = db.query(Patient).filter(Patient.user_id == user.user_id).all()
        
        # Group by patient_id (handle duplicates)
        for patient_id_str in df['patient_id'].unique():
            patient_df = df[df['patient_id'] == patient_id_str]
            first_row = patient_df.iloc[0]
            
            # Extract metadata
            age = None
            if 'age' in first_row and pd.notna(first_row.get('age')):
                try:
                    age = int(float(first_row.get('age')))
                except:
                    age = None
            
            gender = None
            if 'gender' in first_row and pd.notna(first_row.get('gender')):
                gender_val = str(first_row.get('gender')).upper()
                if gender_val in ['M', 'F', 'OTHER']:
                    gender = gender_val if gender_val != 'OTHER' else 'Other'
            
            cancer_type = None
            if 'cancer_type' in first_row and pd.notna(first_row.get('cancer_type')):
                cancer_type = str(first_row.get('cancer_type'))
            
            # Try to find existing patient that matches cancer_type and doesn't have complete metadata
            # Update the first patient that matches cancer_type and needs metadata
            patient_to_update = None
            for patient in existing_patients:
                if patient.cancer_type == cancer_type:
                    # Check if patient needs metadata update
                    if (patient.age is None and age is not None) or \
                       (patient.gender is None and gender is not None) or \
                       (patient.cancer_type != cancer_type and cancer_type is not None):
                        patient_to_update = patient
                        break
            
            if patient_to_update:
                # Update existing patient
                if age is not None:
                    patient_to_update.age = age
                if gender is not None:
                    patient_to_update.gender = gender
                if cancer_type is not None:
                    patient_to_update.cancer_type = cancer_type
                updated += 1
            else:
                # Create new patient if no match found
                # (This happens if metadata file is imported before omics files)
                patient = Patient(
                    user_id=user.user_id,
                    age=age,
                    gender=gender,
                    cancer_type=cancer_type,
                    clinical_info=None
                )
                db.add(patient)
                created += 1
        
        db.commit()
        if updated > 0:
            print(f"SUCCESS: Metadata updated for {updated} patients")
        if created > 0:
            print(f"SUCCESS: Metadata created {created} new patients")
        if updated == 0 and created == 0:
            print("INFO: No metadata changes needed (patients already have complete metadata)")
        return True
        
    except Exception as e:
        db.rollback()
        print(f"WARNING: Error importing metadata: {str(e)}")
        return False

def import_csv_to_database(
    csv_path: str,
    user_email: str = "admin@cancerai.com",
    omics_type: str = None
):
    """
    Import CSV file data into database
    
    Args:
        csv_path: Path to CSV file
        user_email: Email of user to associate data with
        omics_type: Override omics_type if not in CSV (mRNA, miRNA, methylation)
    """
    db: Session = SessionLocal()
    
    try:
        # Get or create user
        user = db.query(User).filter(User.email == user_email).first()
        if not user:
            print(f"❌ User not found: {user_email}")
            print("   Please create user first or use existing user email")
            return False
        
        print(f"✅ Using user: {user.name} ({user.email})")
        
        # Read CSV
        if not Path(csv_path).exists():
            print(f"❌ CSV file not found: {csv_path}")
            return False
        
        df = pd.read_csv(csv_path)
        print(f"📊 Loaded {len(df)} rows from {csv_path}")
        
        # Check if this is a metadata file (has patient_id but no gene_name/value)
        is_metadata_file = 'patient_id' in df.columns and 'gene_name' not in df.columns and 'value' not in df.columns
        
        if is_metadata_file:
            print(f"📋 Detected metadata file - updating patient metadata only")
            return import_patient_metadata(df, user, db)
        
        # Validate required columns for omics data
        required_columns = ['patient_id', 'gene_name', 'value']
        missing = [col for col in required_columns if col not in df.columns]
        if missing:
            print(f"⚠️  Skipping file - Missing required columns: {', '.join(missing)}")
            print(f"   This file doesn't contain omics data. If it's metadata, it will be handled separately.")
            return False
        
        # Determine omics_type
        if omics_type:
            omics_type_str = omics_type
        elif 'omics_type' in df.columns:
            omics_type_str = df['omics_type'].iloc[0] if len(df) > 0 else 'mRNA'
        elif 'mirna' in csv_path.lower():
            omics_type_str = 'miRNA'
        elif 'methylation' in csv_path.lower():
            omics_type_str = 'methylation'
        else:
            omics_type_str = 'mRNA'
        
        # Map to enum
        omics_type_map = {
            'mRNA': OmicsType.mRNA,
            'miRNA': OmicsType.miRNA,
            'methylation': OmicsType.methylation
        }
        omics_enum = omics_type_map.get(omics_type_str, OmicsType.mRNA)
        
        print(f"📝 Processing omics_type: {omics_type_str}")
        
        # Get unique patient IDs
        patient_ids = df['patient_id'].unique()
        print(f"👥 Found {len(patient_ids)} unique patients")
        
        new_patients = 0
        new_omics_records = 0
        skipped_omics = 0
        
        # Process each patient
        for patient_id_str in patient_ids:
            patient_df = df[df['patient_id'] == patient_id_str]
            
            # Get patient metadata (from first row)
            first_row = patient_df.iloc[0]
            
            # Check if patient already exists (by checking omics data with same patient_id pattern)
            # Since patient_id in DB is auto-increment, we'll use a different approach
            # We'll create a mapping: patient_id_str -> database patient_id
            # For now, create new patient for each unique patient_id_str
            
            # Extract age, gender, cancer_type
            age = None
            if 'age' in first_row and pd.notna(first_row['age']):
                try:
                    age = int(float(first_row['age']))
                except:
                    age = None
            
            gender = None
            if 'gender' in first_row and pd.notna(first_row['gender']):
                gender_val = str(first_row['gender']).upper()
                if gender_val in ['M', 'F', 'OTHER']:
                    gender = gender_val if gender_val != 'OTHER' else 'Other'
            
            cancer_type = None
            if 'cancer_type' in first_row and pd.notna(first_row['cancer_type']):
                cancer_type = str(first_row['cancer_type'])
            
            clinical_info = None
            if 'clinical_info' in first_row and pd.notna(first_row['clinical_info']):
                clinical_info = str(first_row['clinical_info'])
            
            # Create patient record
            patient = Patient(
                user_id=user.user_id,
                age=age,
                gender=gender,
                cancer_type=cancer_type,
                clinical_info=clinical_info
            )
            db.add(patient)
            db.flush()  # Get patient_id
            
            new_patients += 1
            
            # Store mapping for this patient_id_str
            patient_mapping = {patient_id_str: patient.patient_id}
            
            # Insert omics data
            for _, row in patient_df.iterrows():
                gene_name = str(row['gene_name'])
                value = float(row['value'])
                
                # Check if this omics record already exists
                existing = db.query(OmicsData).filter(
                    OmicsData.patient_id == patient.patient_id,
                    OmicsData.gene_name == gene_name,
                    OmicsData.omics_type == omics_enum
                ).first()
                
                if existing:
                    # Update existing record
                    existing.value = value
                    skipped_omics += 1
                else:
                    # Create new omics record
                    omics_record = OmicsData(
                        patient_id=patient.patient_id,
                        gene_name=gene_name,
                        value=value,
                        omics_type=omics_enum
                    )
                    db.add(omics_record)
                    new_omics_records += 1
        
        # Commit all changes
        db.commit()
        
        print("\n" + "="*60)
        print("✅ Import Summary:")
        print(f"   Patients created: {new_patients}")
        print(f"   Omics records added: {new_omics_records}")
        print(f"   Omics records skipped (duplicates): {skipped_omics}")
        print(f"   Omics type: {omics_type_str}")
        print("="*60)
        
        return True
        
    except Exception as e:
        db.rollback()
        print(f"❌ Error importing data: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        db.close()

def import_all_csv_files(data_dir: str = None, user_email: str = "admin@cancerai.com"):
    """
    Import all CSV files from data directory
    """
    if data_dir is None:
        # Default to project data directory
        project_root = Path(__file__).parent.parent.parent
        data_dir = project_root / "data"
    else:
        data_dir = Path(data_dir)
    
    if not data_dir.exists():
        print(f"❌ Data directory not found: {data_dir}")
        return False
    
    csv_files = list(data_dir.glob("*.csv"))
    if not csv_files:
        print(f"❌ No CSV files found in {data_dir}")
        return False
    
    print(f"📁 Found {len(csv_files)} CSV files")
    
    # Filter out metadata files (files without gene_name/value)
    omics_files = []
    metadata_files = []
    
    for csv_file in csv_files:
        try:
            # Quick check - read first few lines
            df_check = pd.read_csv(csv_file, nrows=1)
            # Check if it has omics data (gene_name and value)
            has_omics = 'gene_name' in df_check.columns and 'value' in df_check.columns
            # Check if it's metadata only (has patient_id but no gene_name/value)
            is_metadata_only = 'patient_id' in df_check.columns and not has_omics
            
            if has_omics:
                omics_files.append(csv_file)
            elif is_metadata_only:
                metadata_files.append(csv_file)
        except Exception as e:
            # If can't read, skip it
            print(f"WARNING: Could not read {csv_file.name}: {str(e)}")
            continue
    
    print(f"   Omics data files: {len(omics_files)}")
    print(f"   Metadata files: {len(metadata_files)} (will be processed)")
    
    # Import omics files first
    success_count = 0
    for csv_file in omics_files:
        print(f"\n{'='*60}")
        print(f"Processing omics file: {csv_file.name}")
        print(f"{'='*60}")
        if import_csv_to_database(str(csv_file), user_email=user_email):
            success_count += 1
    
    # Process metadata files (update patient metadata)
    metadata_count = 0
    if metadata_files:
        print(f"\n{'='*60}")
        print(f"Processing metadata files (updating patient information):")
        print(f"{'='*60}")
        for csv_file in metadata_files:
            print(f"\nProcessing metadata: {csv_file.name}")
            try:
                if import_csv_to_database(str(csv_file), user_email=user_email):
                    metadata_count += 1
                    print(f"  SUCCESS: {csv_file.name} processed")
                else:
                    print(f"  WARNING: {csv_file.name} had issues (may already be in omics files)")
            except Exception as e:
                print(f"  ERROR processing {csv_file.name}: {str(e)}")
    
    print(f"\n✅ Successfully imported {success_count}/{len(omics_files)} omics files")
    if metadata_count > 0:
        print(f"✅ Processed {metadata_count}/{len(metadata_files)} metadata files")
    
    return success_count > 0

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Import CSV data to database")
    parser.add_argument("--csv", type=str, help="Path to CSV file")
    parser.add_argument("--data-dir", type=str, help="Path to data directory (imports all CSVs)")
    parser.add_argument("--user", type=str, default="admin@cancerai.com", help="User email")
    parser.add_argument("--omics-type", type=str, help="Override omics_type (mRNA, miRNA, methylation)")
    
    args = parser.parse_args()
    
    # Initialize database connection
    init_db()
    
    if args.data_dir:
        # Import all CSV files
        import_all_csv_files(args.data_dir, args.user)
    elif args.csv:
        # Import single CSV file
        import_csv_to_database(args.csv, args.user, args.omics_type)
    else:
        # Default: import all CSV files from data directory
        print("No CSV file or directory specified. Importing all CSV files from data/ directory...")
        import_all_csv_files(user_email=args.user)

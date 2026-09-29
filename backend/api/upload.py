"""
File Upload API Endpoints
Handles CSV/Excel upload and triggers auto-training
"""

from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, status, BackgroundTasks
from fastapi.security import HTTPBearer
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime
import pandas as pd
import numpy as np
from io import StringIO
import os

from database.connection import get_db
from database.models import User, Patient, OmicsData, OmicsType, TrainingJob, JobStatus
from api.auth import get_current_user

from utils.ml_imports import trigger_auto_training

router = APIRouter()
security = HTTPBearer()

@router.post("/csv")
async def upload_csv(
    file: UploadFile = File(...),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Upload CSV file with multi-omics data"""
    
    if not file.filename.endswith('.csv'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only CSV files are supported"
        )
    
    try:
        # Read CSV content
        content = await file.read()
        df = pd.read_csv(StringIO(content.decode('utf-8')))
        # Normalize column names (strip spaces, BOM)
        df.columns = df.columns.str.strip().str.replace('\ufeff', '')
        
        # Support two formats: (1) multi-omics CSV (patient_id, gene_name, value), (2) metadata-only (patient_id, cancer_type, age, gender)
        has_patient_id = "patient_id" in df.columns
        has_omics = "gene_name" in df.columns and "value" in df.columns
        if not has_patient_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="CSV must contain column: patient_id"
            )
        if not has_omics:
            # Metadata-only CSV (patient_id, cancer_type, age, gender): add patients only, one per patient_id
            new_patients = 0
            for patient_id_str in df["patient_id"].unique():
                patient_id_str = str(patient_id_str).strip()
                if not patient_id_str:
                    continue
                row = df[df["patient_id"] == patient_id_str].iloc[0]
                age = None
                if "age" in row and pd.notna(row.get("age")):
                    try:
                        age = int(float(row["age"]))
                    except Exception:
                        age = None
                gender = None
                if "gender" in row and pd.notna(row.get("gender")):
                    g = str(row["gender"]).upper()
                    gender = g if g in ["M", "F", "OTHER"] else "Other"
                cancer_type = str(row["cancer_type"]).strip() if "cancer_type" in row and pd.notna(row.get("cancer_type")) else None
                clinical_info = str(row["clinical_info"]).strip() if "clinical_info" in row and pd.notna(row.get("clinical_info")) else None
                patient = Patient(
                    user_id=current_user.user_id,
                    age=age,
                    gender=gender,
                    cancer_type=cancer_type,
                    clinical_info=clinical_info
                )
                db.add(patient)
                new_patients += 1
            db.commit()
            return {
                "message": "Patients added (metadata only). Upload cancer_multiomics_data.csv to add omics data and train the model.",
                "patients_added": new_patients,
                "omics_records_added": 0,
                "omics_type": "none",
                "auto_training_triggered": False,
                "job_id": None
            }
        
        # Per-row omics_type when column exists (multi-omics CSV: mRNA, methylation, miRNA in same file)
        has_omics_column = "omics_type" in df.columns
        omics_type_str_default = "mRNA"
        if not has_omics_column and "mirna" in file.filename.lower():
            omics_type_str_default = "miRNA"
        elif not has_omics_column and "methylation" in file.filename.lower():
            omics_type_str_default = "methylation"
        
        omics_type_map = {
            "mRNA": OmicsType.mRNA,
            "miRNA": OmicsType.miRNA,
            "methylation": OmicsType.methylation,
        }
        
        # Process and store data
        new_patients = 0
        new_omics_records = 0
        
        # Get unique patient IDs
        patient_ids = df["patient_id"].unique()
        
        # Track patient mappings: CSV patient_id_str -> DB patient_id
        patient_mapping = {}
        
        for patient_id_str in patient_ids:
            # Get patient data from first row
            patient_data = df[df["patient_id"] == patient_id_str].iloc[0]
            
            # Extract patient metadata
            age = None
            if "age" in patient_data and pd.notna(patient_data.get("age")):
                try:
                    age = int(float(patient_data.get("age")))
                except:
                    age = None
            
            gender = None
            if "gender" in patient_data and pd.notna(patient_data.get("gender")):
                gender_val = str(patient_data.get("gender")).upper()
                if gender_val in ["M", "F", "OTHER"]:
                    gender = gender_val if gender_val != "OTHER" else "Other"
            
            cancer_type = None
            if "cancer_type" in patient_data and pd.notna(patient_data.get("cancer_type")):
                cancer_type = str(patient_data.get("cancer_type"))
            
            clinical_info = None
            if "clinical_info" in patient_data and pd.notna(patient_data.get("clinical_info")):
                clinical_info = str(patient_data.get("clinical_info"))
            
            # Create new patient (always create new for CSV uploads to avoid conflicts)
            # In production, you might want to check for duplicates based on other criteria
            patient = Patient(
                user_id=current_user.user_id,
                age=age,
                gender=gender,
                cancer_type=cancer_type,
                clinical_info=clinical_info
            )
            db.add(patient)
            db.flush()  # Get patient_id
            
            # Store mapping
            patient_mapping[patient_id_str] = patient.patient_id
            new_patients += 1
            
            # Insert omics data for this patient (per-row omics_type for multi-omics CSV)
            patient_df = df[df["patient_id"] == patient_id_str]
            for _, row in patient_df.iterrows():
                gene_name = str(row["gene_name"])
                value = float(row["value"])
                if has_omics_column and pd.notna(row.get("omics_type")):
                    row_omics_str = str(row["omics_type"]).strip()
                else:
                    row_omics_str = omics_type_str_default
                row_omics = omics_type_map.get(row_omics_str, OmicsType.mRNA)
                
                existing = db.query(OmicsData).filter(
                    OmicsData.patient_id == patient.patient_id,
                    OmicsData.gene_name == gene_name,
                    OmicsData.omics_type == row_omics
                ).first()
                
                if not existing:
                    omics_record = OmicsData(
                        patient_id=patient.patient_id,
                        gene_name=gene_name,
                        value=value,
                        omics_type=row_omics
                    )
                    db.add(omics_record)
                    new_omics_records += 1
        
        db.commit()
        
        # Trigger auto-training if new data added
        job_id = None
        if new_omics_records > 0:
            # Create training job record
            from datetime import datetime
            training_job = TrainingJob(
                trigger_type="new_data",
                status=JobStatus.queued,
                new_samples_count=new_patients,
                created_at=datetime.now()
            )
            db.add(training_job)
            db.commit()
            job_id = training_job.job_id
            
            # Trigger background training using FastAPI BackgroundTasks
            try:
                background_tasks.add_task(trigger_auto_training, training_job.job_id)
            except Exception as e:
                print(f"Warning: Could not trigger auto-training: {e}")
        
        return {
            "message": "File uploaded successfully",
            "patients_added": new_patients,
            "omics_records_added": new_omics_records,
            "omics_type": "multi" if has_omics_column else omics_type_str_default,
            "auto_training_triggered": new_omics_records > 0,
            "job_id": job_id
        }
        
    except HTTPException:
        raise
    except pd.errors.EmptyDataError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="CSV file is empty"
        )
    except Exception as e:
        db.rollback()
        err_msg = str(e)
        # Likely metadata-only CSV (no gene_name/value) that passed column check
        if "gene_name" in err_msg or "value" in err_msg or "KeyError" in err_msg:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    "CSV must contain columns: patient_id, gene_name, value (and optionally omics_type, cancer_type). "
                    "patient_metadata.csv is metadata only. Use cancer_multiomics_data.csv from the data/ folder."
                )
            )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing file: {err_msg}"
        )

@router.post("/manual")
async def upload_manual_data(
    data: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Upload patient data manually (form input)"""
    
    try:
        # Create patient record
        patient = Patient(
            user_id=current_user.user_id,
            age=data.get("age"),
            gender=data.get("gender"),
            cancer_type=data.get("cancer_type"),
            clinical_info=data.get("clinical_info")
        )
        db.add(patient)
        db.flush()
        
        # Add omics data
        omics_data_list = data.get("omics_data", [])
        for omics_item in omics_data_list:
            omics_type_map = {
                "mRNA": OmicsType.mRNA,
                "miRNA": OmicsType.miRNA,
                "methylation": OmicsType.methylation
            }
            omics_type = omics_type_map.get(omics_item.get("omics_type", "mRNA"), OmicsType.mRNA)
            
            omics_record = OmicsData(
                patient_id=patient.patient_id,
                gene_name=omics_item["gene_name"],
                value=float(omics_item["value"]),
                omics_type=omics_type
            )
            db.add(omics_record)
        
        db.commit()
        
        return {
            "message": "Data uploaded successfully",
            "patient_id": patient.patient_id
        }
        
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error uploading data: {str(e)}"
        )

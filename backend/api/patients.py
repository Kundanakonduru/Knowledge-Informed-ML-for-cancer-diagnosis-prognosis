"""
Patient Management API Endpoints
"""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List

from database.connection import get_db
from database.models import User, Patient, OmicsData, UserRole
from api.auth import get_current_user
from sqlalchemy import exists

router = APIRouter()
security = HTTPBearer()

class PatientCreate(BaseModel):
    age: Optional[int] = None
    gender: Optional[str] = None
    cancer_type: Optional[str] = None
    clinical_info: Optional[str] = None

class PatientResponse(BaseModel):
    patient_id: int
    age: Optional[int]
    gender: Optional[str]
    cancer_type: Optional[str]
    clinical_info: Optional[str]

@router.post("/", response_model=PatientResponse)
async def create_patient(
    patient_data: PatientCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new patient record"""
    
    patient = Patient(
        user_id=current_user.user_id,
        age=patient_data.age,
        gender=patient_data.gender,
        cancer_type=patient_data.cancer_type,
        clinical_info=patient_data.clinical_info
    )
    
    db.add(patient)
    db.commit()
    db.refresh(patient)
    
    return {
        "patient_id": patient.patient_id,
        "age": patient.age,
        "gender": patient.gender,
        "cancer_type": patient.cancer_type,
        "clinical_info": patient.clinical_info
    }

@router.get("/", response_model=List[PatientResponse])
async def list_patients(
    skip: int = 0,
    limit: int = 500,
    with_omics_only: bool = False,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List patients. Use with_omics_only=true to only return patients that have omics data (for prediction dropdown)."""
    
    q = db.query(Patient)
    # If not admin, restrict to own patients
    if current_user.role != UserRole.admin:
        q = q.filter(Patient.user_id == current_user.user_id)
        
    if with_omics_only:
        # Only patients that have at least one OmicsData record (can run prediction)
        q = q.filter(exists().where(OmicsData.patient_id == Patient.patient_id))
    patients = q.order_by(Patient.patient_id.desc()).offset(skip).limit(limit).all()
    
    return [
        {
            "patient_id": p.patient_id,
            "age": p.age,
            "gender": p.gender,
            "cancer_type": p.cancer_type,
            "clinical_info": p.clinical_info
        }
        for p in patients
    ]

@router.get("/{patient_id}", response_model=PatientResponse)
async def get_patient(
    patient_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get patient by ID"""
    
    patient = db.query(Patient).filter(
        Patient.patient_id == patient_id,
        Patient.user_id == current_user.user_id
    ).first()
    
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Patient not found"
        )
    
    return {
        "patient_id": patient.patient_id,
        "age": patient.age,
        "gender": patient.gender,
        "cancer_type": patient.cancer_type,
        "clinical_info": patient.clinical_info
    }

@router.get("/{patient_id}/omics")
async def get_patient_omics(
    patient_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get omics data for a patient"""
    
    patient = db.query(Patient).filter(
        Patient.patient_id == patient_id,
        Patient.user_id == current_user.user_id
    ).first()
    
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Patient not found"
        )
    
    omics_data = db.query(OmicsData).filter(
        OmicsData.patient_id == patient_id
    ).all()
    
    return {
        "patient_id": patient_id,
        "omics_data": [
            {
                "omics_id": o.omics_id,
                "gene_name": o.gene_name,
                "value": o.value,
                "omics_type": o.omics_type.value,
                "created_at": o.created_at.isoformat()
            }
            for o in omics_data
        ]
    }

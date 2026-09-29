"""
Prediction API Endpoints
Cancer type prediction and risk scoring
"""

from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from fastapi.security import HTTPBearer
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List

from database.connection import get_db
from database.models import User, Patient, Prediction, ModelRegistry, ModelStatus, UserRole
from api.auth import get_current_user
from utils.ml_imports import predict_cancer_type

router = APIRouter()
security = HTTPBearer()

# Project root (backend's parent)
_BACKEND_DIR = Path(__file__).resolve().parent.parent
_PROJECT_ROOT = _BACKEND_DIR.parent


def _resolve_model_path(model_path_from_db: str) -> Optional[str]:
    """Resolve model file path: try DB path, then project_root/models, then ml_engine/models."""
    p = Path(model_path_from_db)
    if p.exists():
        return str(p)
    basename = p.name
    for folder in [_PROJECT_ROOT / "models", _PROJECT_ROOT / "ml_engine" / "models"]:
        candidate = folder / basename
        if candidate.exists():
            return str(candidate)
    return None


class PredictionRequest(BaseModel):
    patient_id: int

class PredictionResponse(BaseModel):
    prediction_id: int
    patient_id: int
    cancer_type: str
    risk_score: float
    confidence: float
    prognosis_score: Optional[float]
    risk_scores: Optional[dict] = None  # all class probabilities e.g. {"LUAD": 0.27, "BRCA": 0.25, ...}

@router.post("/predict", response_model=PredictionResponse)
async def create_prediction(
    request: PredictionRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Generate cancer prediction for a patient"""
    
    # Get patient
    patient = db.query(Patient).filter(Patient.patient_id == request.patient_id).first()
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Patient not found"
        )
    
    # Get active model
    model = db.query(ModelRegistry).filter(
        ModelRegistry.status == ModelStatus.active
    ).order_by(ModelRegistry.trained_on.desc()).first()
    
    if not model:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "code": "NO_MODEL",
                "detail": "No trained model yet. Train a model first: open Model Training and click 'Trigger Training', or run from project root: python ml_engine/train_from_database.py",
                "action": "train_model",
            },
        )
    
    # Resolve model file path (DB may have old path)
    model_path = _resolve_model_path(model.model_path)
    if not model_path:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "code": "MODEL_FILE_NOT_FOUND",
                "detail": "Model file is missing. Re-train: open Model Training and click 'Trigger Training', or run: python ml_engine/train_from_database.py",
                "action": "train_model",
            },
        )
    
    # Get prediction from ML engine
    try:
        prediction_result = predict_cancer_type(patient.patient_id, db, model_path=model_path)
        
        # Save prediction to database
        prediction = Prediction(
            patient_id=patient.patient_id,
            model_id=model.model_id,
            cancer_type=prediction_result["cancer_type"],
            risk_score=float(prediction_result["risk_score"]),
            confidence=float(prediction_result["confidence"]),
            prognosis_score=prediction_result.get("prognosis_score") and float(prediction_result["prognosis_score"])
        )
        db.add(prediction)
        db.commit()
        db.refresh(prediction)
        
        return {
            "prediction_id": prediction.prediction_id,
            "patient_id": prediction.patient_id,
            "cancer_type": prediction.cancer_type,
            "risk_score": prediction.risk_score,
            "confidence": prediction.confidence,
            "prognosis_score": prediction.prognosis_score,
            "risk_scores": prediction_result.get("risk_scores"),
        }
        
    except ValueError as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Prediction failed: {str(e)}"
        )

@router.get("/predictions/{patient_id}")
async def get_patient_predictions(
    patient_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all predictions for a patient"""
    
    predictions = db.query(Prediction).filter(
        Prediction.patient_id == patient_id
    ).order_by(Prediction.created_at.desc()).all()
    
    return [
        {
            "prediction_id": p.prediction_id,
            "cancer_type": p.cancer_type,
            "risk_score": p.risk_score,
            "confidence": p.confidence,
            "prognosis_score": p.prognosis_score,
            "created_at": p.created_at.isoformat()
        }
        for p in predictions
    ]

@router.get("/predictions")
async def list_all_predictions(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List all predictions for the current user (paginated)"""
    
    q = db.query(Prediction).join(Patient)
    if current_user.role != UserRole.admin:
        q = q.filter(Patient.user_id == current_user.user_id)
    
    predictions = q.order_by(Prediction.created_at.desc()).offset(skip).limit(limit).all()
    
    return [
        {
            "prediction_id": p.prediction_id,
            "patient_id": p.patient_id,
            "cancer_type": p.cancer_type,
            "risk_score": p.risk_score,
            "confidence": p.confidence,
            "created_at": p.created_at.isoformat()
        }
        for p in predictions
    ]

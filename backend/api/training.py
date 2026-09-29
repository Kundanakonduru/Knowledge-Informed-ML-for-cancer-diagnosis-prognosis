"""
Training API Endpoints
Model training, versioning, status tracking
"""

from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from fastapi.security import HTTPBearer
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime

from database.connection import get_db
from database.models import User, ModelRegistry, TrainingJob, ModelStatus, JobStatus
from api.auth import get_current_user
from utils.ml_imports import trigger_auto_training

router = APIRouter()
security = HTTPBearer()

@router.post("/trigger")
async def trigger_training(
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Manually trigger model training (Admin only)"""
    
    user_role_str = current_user.role.value if hasattr(current_user.role, 'value') else str(current_user.role)
    if user_role_str != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admin can trigger training"
        )
    
    # Create training job
    training_job = TrainingJob(
        trigger_type="manual",
        status=JobStatus.queued,
        created_at=datetime.now()
    )
    db.add(training_job)
    db.commit()

    # Trigger background training using FastAPI BackgroundTasks (no Celery .delay here)
    # This will run training in the background without blocking the request.
    background_tasks.add_task(trigger_auto_training, training_job.job_id)
    
    return {
        "message": "Training job queued",
        "job_id": training_job.job_id
    }

@router.get("/jobs")
async def list_training_jobs(
    limit: Optional[int] = 20,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List recent training jobs (for upload→train pipeline status)"""
    
    jobs = db.query(TrainingJob).order_by(TrainingJob.created_at.desc()).limit(limit).all()
    
    return [
        {
            "job_id": j.job_id,
            "status": j.status.value if hasattr(j.status, 'value') else str(j.status),
            "trigger_type": j.trigger_type.value if hasattr(j.trigger_type, 'value') else str(j.trigger_type),
            "new_samples_count": j.new_samples_count,
            "accuracy_after": j.accuracy_after,
            "error_message": j.error_message,
            "created_at": j.created_at.isoformat() if j.created_at else None,
            "started_at": j.started_at.isoformat() if j.started_at else None,
            "completed_at": j.completed_at.isoformat() if j.completed_at else None,
        }
        for j in jobs
    ]

@router.get("/status/{job_id}")
async def get_training_status(
    job_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get training job status"""
    
    job = db.query(TrainingJob).filter(TrainingJob.job_id == job_id).first()
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Training job not found"
        )
    
    status_str = job.status.value if hasattr(job.status, 'value') else str(job.status)
    return {
        "job_id": job.job_id,
        "status": status_str,
        "trigger_type": job.trigger_type,
        "accuracy_before": job.accuracy_before,
        "accuracy_after": job.accuracy_after,
        "started_at": job.started_at.isoformat() if job.started_at else None,
        "completed_at": job.completed_at.isoformat() if job.completed_at else None,
        "error_message": job.error_message
    }

@router.get("/models")
async def list_models(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List all trained models"""
    
    models = db.query(ModelRegistry).order_by(ModelRegistry.trained_on.desc()).all()
    
    return [
        {
            "model_id": m.model_id,
            "version": m.version,
            "model_type": m.model_type,
            "accuracy": m.accuracy,
            "training_samples": m.training_samples,
            "trained_on": m.trained_on.isoformat() if m.trained_on else None,
            "status": m.status.value if hasattr(m.status, 'value') else str(m.status)
        }
        for m in models
    ]

@router.get("/models/active")
async def get_active_model(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get currently active model"""
    
    model = db.query(ModelRegistry).filter(
        ModelRegistry.status == ModelStatus.active
    ).order_by(ModelRegistry.trained_on.desc()).first()
    
    if not model:
        # Return null instead of 404 to allow frontend to handle gracefully
        return None
    
    return {
        "model_id": model.model_id,
        "version": model.version,
        "model_type": model.model_type,
        "accuracy": model.accuracy,
        "training_samples": model.training_samples,
        "trained_on": model.trained_on.isoformat() if model.trained_on else None,
        "status": model.status.value if hasattr(model.status, 'value') else str(model.status)
    }

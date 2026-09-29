"""
Explanation API Endpoints
Explainable AI - Gene importance, pathways, attention weights
"""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer
from sqlalchemy.orm import Session
from typing import List

from database.connection import get_db
from database.models import User, Prediction, Explanation
from api.auth import get_current_user
from utils.ml_imports import generate_explanations

router = APIRouter()
security = HTTPBearer()

@router.get("/prediction/{prediction_id}")
async def get_prediction_explanations(
    prediction_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get explanations for a prediction"""
    
    prediction = db.query(Prediction).filter(
        Prediction.prediction_id == prediction_id
    ).first()
    
    if not prediction:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Prediction not found"
        )
    
    # Get or generate explanations
    explanations = db.query(Explanation).filter(
        Explanation.prediction_id == prediction_id
    ).all()
    
    # If no explanations exist, generate them
    if not explanations:
        try:
            explanations_data = generate_explanations(prediction_id, db)
            # Save to database
            for exp_data in explanations_data:
                exp = Explanation(
                    prediction_id=prediction_id,
                    gene_name=exp_data.get("gene_name"),
                    importance_score=exp_data.get("importance_score"),
                    pathway_name=exp_data.get("pathway_name"),
                    attention_weight=exp_data.get("attention_weight"),
                    explanation_type=exp_data.get("explanation_type")
                )
                db.add(exp)
            db.commit()
            
            # Reload explanations
            explanations = db.query(Explanation).filter(
                Explanation.prediction_id == prediction_id
            ).all()
        except Exception as e:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to generate explanations: {str(e)}"
            )
    
    # Group by type
    gene_explanations = [e for e in explanations if e.explanation_type.value == "gene"]
    pathway_explanations = [e for e in explanations if e.explanation_type.value == "pathway"]
    attention_explanations = [e for e in explanations if e.explanation_type.value == "attention"]
    
    return {
        "prediction_id": prediction_id,
        "gene_importance": [
            {
                "gene_name": e.gene_name,
                "importance_score": e.importance_score
            }
            for e in sorted(gene_explanations, key=lambda x: x.importance_score or 0, reverse=True)[:20]
        ],
        "pathway_activation": [
            {
                "pathway_name": e.pathway_name,
                "attention_weight": e.attention_weight
            }
            for e in sorted(pathway_explanations, key=lambda x: x.attention_weight or 0, reverse=True)[:10]
        ],
        "attention_weights": [
            {
                "gene_name": e.gene_name,
                "attention_weight": e.attention_weight
            }
            for e in sorted(attention_explanations, key=lambda x: x.attention_weight or 0, reverse=True)[:20]
        ]
    }

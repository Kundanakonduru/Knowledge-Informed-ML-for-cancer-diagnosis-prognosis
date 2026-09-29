"""
Chatbot API Endpoints
Clinical AI Assistant with RAG
"""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional

from database.connection import get_db
from database.models import User, ChatHistory, Prediction
from api.auth import get_current_user
from chatbot.rag_assistant import generate_chat_response

router = APIRouter()
security = HTTPBearer()

class ChatRequest(BaseModel):
    query: str
    patient_id: Optional[int] = None
    prediction_id: Optional[int] = None

class ChatResponse(BaseModel):
    response: str
    chat_id: int

@router.post("/query", response_model=ChatResponse)
async def chat_query(
    request: ChatRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Chat with clinical AI assistant"""
    
    # Validate prediction_id if provided
    prediction = None
    if request.prediction_id:
        prediction = db.query(Prediction).filter(
            Prediction.prediction_id == request.prediction_id
        ).first()
        if not prediction:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Prediction not found"
            )
    
    # Generate response using RAG
    try:
        response_text = generate_chat_response(
            query=request.query,
            user_id=current_user.user_id,
            patient_id=request.patient_id,
            prediction_id=request.prediction_id,
            db=db
        )
        
        # Save chat history
        chat_entry = ChatHistory(
            user_id=current_user.user_id,
            patient_id=request.patient_id,
            prediction_id=request.prediction_id,
            query=request.query,
            response=response_text
        )
        db.add(chat_entry)
        db.commit()
        db.refresh(chat_entry)
        
        return {
            "response": response_text,
            "chat_id": chat_entry.chat_id
        }
        
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Chat query failed: {str(e)}"
        )

@router.get("/history")
async def get_chat_history(
    patient_id: Optional[int] = None,
    limit: int = 50,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get chat history for user/patient"""
    
    query = db.query(ChatHistory).filter(
        ChatHistory.user_id == current_user.user_id
    )
    
    if patient_id:
        query = query.filter(ChatHistory.patient_id == patient_id)
    
    history = query.order_by(ChatHistory.created_at.desc()).limit(limit).all()
    
    return [
        {
            "chat_id": h.chat_id,
            "query": h.query,
            "response": h.response,
            "patient_id": h.patient_id,
            "prediction_id": h.prediction_id,
            "created_at": h.created_at.isoformat()
        }
        for h in history
    ]

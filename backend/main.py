"""
FastAPI Backend for Knowledge-Informed Cancer Diagnosis System
Main Application Entry Point
"""

from fastapi import FastAPI, Depends, HTTPException, status, UploadFile, File, BackgroundTasks, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import JSONResponse, Response
import base64
from sqlalchemy.orm import Session
from typing import List, Optional
import os
from dotenv import load_dotenv

from database.connection import get_db, init_db
from api.auth import router as auth_router
from api.patients import router as patients_router
from api.upload import router as upload_router
from api.training import router as training_router
from api.prediction import router as prediction_router
from api.explanation import router as explanation_router
from api.chatbot import router as chatbot_router

from utils.ml_imports import trigger_auto_training

load_dotenv()

app = FastAPI(
    title="Knowledge-Informed Cancer Diagnosis API",
    description="REST API for Cancer Diagnosis & Prognosis System",
    version="1.0.0"
)

# CORS Configuration - Must be added before routes
# Note: When allow_credentials=True, you cannot use wildcard (*) for origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
        "http://localhost:3001",  # Alternative React port
    ],  # React dev server ports
    allow_credentials=True,
    allow_methods=["*"],  # Allow all methods including OPTIONS
    allow_headers=["*"],  # Allow all headers
    expose_headers=["*"],
    max_age=3600,
)

# Security
security = HTTPBearer()

# Include routers
app.include_router(auth_router, prefix="/api/auth", tags=["Authentication"])
app.include_router(patients_router, prefix="/api/patients", tags=["Patients"])
app.include_router(upload_router, prefix="/api/upload", tags=["Upload"])
app.include_router(training_router, prefix="/api/training", tags=["Training"])
app.include_router(prediction_router, prefix="/api/prediction", tags=["Prediction"])
app.include_router(explanation_router, prefix="/api/explanation", tags=["Explanation"])
app.include_router(chatbot_router, prefix="/api/chatbot", tags=["Chatbot"])

@app.on_event("startup")
async def startup_event():
    """Initialize database on startup"""
    init_db()
    print("🚀 Cancer Diagnosis API started successfully!")

@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "message": "Knowledge-Informed Cancer Diagnosis API",
        "status": "running",
        "version": "1.0.0"
    }

@app.get("/api/health")
async def health_check():
    """Detailed health check"""
    return {
        "status": "healthy",
        "database": "connected",
        "ml_engine": "ready"
    }

# Minimal 1x1 transparent PNG (avoids 204 No Content and repeated requests)
_FAVICON_PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
)

@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    """Serve minimal favicon so browser caches and logs show 200 OK instead of 204."""
    return Response(content=_FAVICON_PNG, media_type="image/png", status_code=200)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)

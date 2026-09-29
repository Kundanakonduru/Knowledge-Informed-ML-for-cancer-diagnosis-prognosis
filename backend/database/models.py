"""
SQLAlchemy ORM Models
"""

from sqlalchemy import Column, Integer, String, Float, Text, Enum, ForeignKey, TIMESTAMP, Index
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database.connection import Base
import enum

class UserRole(enum.Enum):
    admin = "admin"
    doctor = "doctor"
    researcher = "researcher"

class OmicsType(enum.Enum):
    mRNA = "mRNA"
    miRNA = "miRNA"
    methylation = "methylation"

class ModelStatus(enum.Enum):
    training = "training"
    active = "active"
    archived = "archived"

class JobStatus(enum.Enum):
    queued = "queued"
    running = "running"
    completed = "completed"
    failed = "failed"

class ExplanationType(enum.Enum):
    gene = "gene"
    pathway = "pathway"
    attention = "attention"

# User Model
class User(Base):
    __tablename__ = "users"
    
    user_id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    role = Column(Enum(UserRole), nullable=False, default=UserRole.researcher, index=True)
    created_at = Column(TIMESTAMP, server_default=func.now())
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())
    
    # Relationships
    patients = relationship("Patient", back_populates="user", cascade="all, delete-orphan")

# Patient Model
class Patient(Base):
    __tablename__ = "patients"
    
    patient_id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False, index=True)
    age = Column(Integer)
    gender = Column(Enum("M", "F", "Other"))
    cancer_type = Column(String(100), index=True)
    clinical_info = Column(Text)
    created_at = Column(TIMESTAMP, server_default=func.now())
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())
    
    # Relationships
    user = relationship("User", back_populates="patients")
    omics_data = relationship("OmicsData", back_populates="patient", cascade="all, delete-orphan")
    predictions = relationship("Prediction", back_populates="patient", cascade="all, delete-orphan")

# Omics Data Model
class OmicsData(Base):
    __tablename__ = "omics_data"
    
    omics_id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("patients.patient_id", ondelete="CASCADE"), nullable=False, index=True)
    gene_name = Column(String(255), nullable=False, index=True)
    value = Column(Float, nullable=False)
    omics_type = Column(Enum(OmicsType), nullable=False, index=True)
    created_at = Column(TIMESTAMP, server_default=func.now())
    
    # Relationships
    patient = relationship("Patient", back_populates="omics_data")
    
    # Composite index
    __table_args__ = (Index('idx_patient_gene', 'patient_id', 'gene_name', 'omics_type'),)

# Model Registry Model
class ModelRegistry(Base):
    __tablename__ = "model_registry"
    
    model_id = Column(Integer, primary_key=True, index=True)
    version = Column(String(50), unique=True, nullable=False)
    model_type = Column(String(100), nullable=False, default="GAT")
    accuracy = Column(Float, index=True)
    training_samples = Column(Integer)
    trained_on = Column(TIMESTAMP, server_default=func.now())
    model_path = Column(String(500), nullable=False)
    status = Column(Enum(ModelStatus), default=ModelStatus.active, index=True)
    created_at = Column(TIMESTAMP, server_default=func.now())

# Prediction Model
class Prediction(Base):
    __tablename__ = "predictions"
    
    prediction_id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("patients.patient_id", ondelete="CASCADE"), nullable=False, index=True)
    model_id = Column(Integer, ForeignKey("model_registry.model_id", ondelete="CASCADE"), nullable=False)
    cancer_type = Column(String(100), nullable=False, index=True)
    risk_score = Column(Float, nullable=False, index=True)
    confidence = Column(Float)
    prognosis_score = Column(Float)
    created_at = Column(TIMESTAMP, server_default=func.now())
    
    # Relationships
    patient = relationship("Patient", back_populates="predictions")
    explanations = relationship("Explanation", back_populates="prediction", cascade="all, delete-orphan")

# Explanation Model
class Explanation(Base):
    __tablename__ = "explanations"
    
    explain_id = Column(Integer, primary_key=True, index=True)
    prediction_id = Column(Integer, ForeignKey("predictions.prediction_id", ondelete="CASCADE"), nullable=False, index=True)
    gene_name = Column(String(255), index=True)
    importance_score = Column(Float)
    pathway_name = Column(String(255), index=True)
    attention_weight = Column(Float)
    explanation_type = Column(Enum(ExplanationType), nullable=False)
    created_at = Column(TIMESTAMP, server_default=func.now())
    
    # Relationships
    prediction = relationship("Prediction", back_populates="explanations")

# Training Job Model
class TrainingJob(Base):
    __tablename__ = "training_jobs"
    
    job_id = Column(Integer, primary_key=True, index=True)
    trigger_type = Column(Enum("new_data", "manual", "threshold"), nullable=False, index=True)
    status = Column(Enum(JobStatus), default=JobStatus.queued, index=True)
    model_id = Column(Integer, ForeignKey("model_registry.model_id", ondelete="SET NULL"))
    new_samples_count = Column(Integer)
    accuracy_before = Column(Float)
    accuracy_after = Column(Float)
    started_at = Column(TIMESTAMP)
    completed_at = Column(TIMESTAMP)
    error_message = Column(Text)
    created_at = Column(TIMESTAMP, server_default=func.now())

# Chat History Model
class ChatHistory(Base):
    __tablename__ = "chat_history"
    
    chat_id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False, index=True)
    patient_id = Column(Integer, ForeignKey("patients.patient_id", ondelete="SET NULL"), index=True)
    prediction_id = Column(Integer, ForeignKey("predictions.prediction_id", ondelete="SET NULL"))
    query = Column(Text, nullable=False)
    response = Column(Text, nullable=False)
    created_at = Column(TIMESTAMP, server_default=func.now())

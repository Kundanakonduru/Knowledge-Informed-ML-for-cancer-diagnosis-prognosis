"""
Authentication API Endpoints
Login, Register, Token Management
"""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr
from datetime import datetime, timedelta
from jose import JWTError, jwt
import bcrypt
from typing import Optional

from database.connection import get_db
from database.models import User, UserRole

router = APIRouter()
security = HTTPBearer()

# Bcrypt max password length is 72 bytes
BCRYPT_MAX_PASSWORD_BYTES = 72

# JWT Configuration
SECRET_KEY = "your-secret-key-change-in-production"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30 * 24 * 60  # 30 days

# Request/Response Models
class UserRegister(BaseModel):
    name: str
    email: EmailStr
    password: str
    role: str = "researcher"  # admin, doctor, researcher

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    user: dict

class UserResponse(BaseModel):
    user_id: int
    name: str
    email: str
    role: str

# Helper Functions (use bcrypt directly to avoid passlib/bcrypt version issues)
def _password_bytes(s: str) -> bytes:
    """Truncate to 72 bytes for bcrypt."""
    return s.encode("utf-8")[:BCRYPT_MAX_PASSWORD_BYTES]

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password against hash."""
    pw = _password_bytes(plain_password)
    stored = hashed_password.encode("utf-8") if isinstance(hashed_password, str) else hashed_password
    return bcrypt.checkpw(pw, stored)

def get_password_hash(password: str) -> str:
    """Hash password (truncated to 72 bytes for bcrypt)."""
    pw = _password_bytes(password)
    return bcrypt.hashpw(pw, bcrypt.gensalt()).decode("utf-8")

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Create JWT access token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
):
    """Get current authenticated user"""
    token = credentials.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: int = payload.get("sub")
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials"
            )
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials"
        )
    
    user = db.query(User).filter(User.user_id == user_id).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )
    return user

# API Endpoints
@router.post("/register", response_model=TokenResponse)
async def register(user_data: UserRegister, db: Session = Depends(get_db)):
    """Register a new user"""
    # Check if email already exists
    existing_user = db.query(User).filter(User.email == user_data.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Validate role
    if user_data.role not in ["admin", "doctor", "researcher"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid role. Must be: admin, doctor, or researcher"
        )
    
    # Create new user
    hashed_password = get_password_hash(user_data.password)
    # Convert role string to UserRole enum
    role_map = {"admin": UserRole.admin, "doctor": UserRole.doctor, "researcher": UserRole.researcher}
    role_enum = role_map.get(user_data.role, UserRole.researcher)
    new_user = User(
        name=user_data.name,
        email=user_data.email,
        password_hash=hashed_password,
        role=role_enum
    )
    
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    # Create access token
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    # Convert enum to string for JSON serialization
    user_role_str = new_user.role.value if hasattr(new_user.role, 'value') else str(new_user.role)
    access_token = create_access_token(
        data={"sub": str(new_user.user_id), "role": user_role_str},
        expires_delta=access_token_expires
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "user_id": new_user.user_id,
            "name": new_user.name,
            "email": new_user.email,
            "role": user_role_str
        }
    }

@router.post("/login", response_model=TokenResponse)
async def login(credentials: UserLogin, db: Session = Depends(get_db)):
    """Login user"""
    user = db.query(User).filter(User.email == credentials.email).first()
    
    if not user or not verify_password(credentials.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )
    
    # Create access token
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    # Convert enum to string for JSON serialization
    user_role_str = user.role.value if hasattr(user.role, 'value') else str(user.role)
    access_token = create_access_token(
        data={"sub": str(user.user_id), "role": user_role_str},
        expires_delta=access_token_expires
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "user_id": user.user_id,
            "name": user.name,
            "email": user.email,
            "role": user_role_str
        }
    }

@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    """Get current user information"""
    # Convert enum to string for JSON serialization
    user_role_str = current_user.role.value if hasattr(current_user.role, 'value') else str(current_user.role)
    return {
        "user_id": current_user.user_id,
        "name": current_user.name,
        "email": current_user.email,
        "role": user_role_str
    }

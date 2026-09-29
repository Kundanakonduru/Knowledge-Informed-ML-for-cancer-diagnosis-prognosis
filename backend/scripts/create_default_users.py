"""
Create default users in the database
Ensures admin, doctor, and researcher users exist with correct passwords
"""

import sys
from pathlib import Path

# Add backend directory to path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from sqlalchemy.orm import Session
import bcrypt
from database.connection import engine, init_db
from database.models import User, UserRole

# Use same bcrypt as auth.py so login always works
BCRYPT_MAX_PASSWORD_BYTES = 72

def _password_bytes(s: str):
    return s.encode("utf-8")[:BCRYPT_MAX_PASSWORD_BYTES]

def get_password_hash(password: str) -> str:
    pw = _password_bytes(password)
    return bcrypt.hashpw(pw, bcrypt.gensalt()).decode("utf-8")

def create_default_users():
    """Create default users if they don't exist"""
    print("="*60)
    print("Creating Default Users")
    print("="*60)
    
    # Initialize database connection
    try:
        from database.connection import engine
        from sqlalchemy import create_engine, text
        import os
        from dotenv import load_dotenv
        
        load_dotenv()
        DB_HOST = os.getenv("DB_HOST", "localhost")
        DB_USER = os.getenv("DB_USER", "root")
        DB_PASSWORD = os.getenv("DB_PASSWORD", "12345")
        DB_NAME = os.getenv("DB_NAME", "cancer_diagnosis_db")
        DB_PORT = int(os.getenv("DB_PORT", 3306))
        
        # Create engine directly
        database_url = f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
        engine = create_engine(database_url, echo=False)
        
        # Test connection
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        print("OK: Database connection established")
    except Exception as e:
        print(f"ERROR: Failed to connect to database: {str(e)}")
        return False
    
    db = Session(bind=engine)
    
    # Default users
    default_users = [
        {
            "name": "Admin User",
            "email": "admin@cancerai.com",
            "password": "admin123",
            "role": "admin"
        },
        {
            "name": "Dr. John Smith",
            "email": "doctor@cancerai.com",
            "password": "admin123",
            "role": "doctor"
        },
        {
            "name": "Researcher Jane",
            "email": "researcher@cancerai.com",
            "password": "admin123",
            "role": "researcher"
        }
    ]
    
    users_created = 0
    users_existing = 0
    
    try:
        for user_data in default_users:
            # Check if user exists
            existing = db.query(User).filter(User.email == user_data["email"]).first()
            
            if existing:
                # Update password hash if needed (in case it's wrong) - use same bcrypt as auth
                hashed_password = get_password_hash(user_data["password"])
                if existing.password_hash != hashed_password:
                    existing.password_hash = hashed_password
                    db.commit()
                    print(f"OK: Updated password for: {user_data['email']}")
                else:
                    print(f"OK: User already exists: {user_data['email']}")
                    users_existing += 1
            else:
                # Create new user - use same bcrypt as auth
                hashed_password = get_password_hash(user_data["password"])
                role_enum = getattr(UserRole, user_data["role"], UserRole.researcher)
                new_user = User(
                    name=user_data["name"],
                    email=user_data["email"],
                    password_hash=hashed_password,
                    role=role_enum
                )
                db.add(new_user)
                users_created += 1
                print(f"OK: Created user: {user_data['email']} ({user_data['role']})")
        
        db.commit()
        
        print("\n" + "="*60)
        print("Summary:")
        print(f"   Users created: {users_created}")
        print(f"   Users existing: {users_existing}")
        print("="*60)
        
        # Verify users
        print("\nVerifying users...")
        for user_data in default_users:
            user = db.query(User).filter(User.email == user_data["email"]).first()
            if user:
                # Test password verification (same as auth.py)
                pw = _password_bytes(user_data["password"])
                stored = user.password_hash.encode("utf-8") if isinstance(user.password_hash, str) else user.password_hash
                if bcrypt.checkpw(pw, stored):
                    print(f"OK: {user_data['email']} - Password verified")
                else:
                    print(f"ERROR: {user_data['email']} - Password verification failed!")
            else:
                print(f"ERROR: {user_data['email']} - User not found!")
        
        db.close()
        return True
        
    except Exception as e:
        print(f"ERROR: Error creating users: {str(e)}")
        db.rollback()
        db.close()
        return False

if __name__ == "__main__":
    success = create_default_users()
    if success:
        print("\nSUCCESS: Default users setup complete!")
        print("\nLogin Credentials:")
        print("   Admin: admin@cancerai.com / admin123")
        print("   Doctor: doctor@cancerai.com / admin123")
        print("   Researcher: researcher@cancerai.com / admin123")
    else:
        print("\nERROR: Failed to create default users")
        sys.exit(1)

"""
Utility module for importing ml_engine modules
Handles path setup to access ml_engine from backend
"""

import sys
from pathlib import Path

# Add project root to path if not already there
_backend_dir = Path(__file__).parent.parent
_project_root = _backend_dir.parent

if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

def import_ml_module(module_name, fallback=None):
    """
    Import a module from ml_engine with fallback
    
    Args:
        module_name: Name of module (e.g., 'auto_train', 'predict')
        fallback: Fallback function/class if import fails
    
    Returns:
        Imported module or fallback
    """
    try:
        module = __import__(f'ml_engine.{module_name}', fromlist=[module_name])
        return module
    except ImportError as e:
        print(f"[Warning] Could not import ml_engine.{module_name}: {e}")
        if fallback:
            return fallback
        return None

# Convenience imports
try:
    from ml_engine.auto_train import trigger_auto_training
except ImportError:
    def trigger_auto_training(job_id=None):
        print(f"[Warning] Auto-training not available. ML engine not found.")
        return None

try:
    from ml_engine.predict import predict_cancer_type
except ImportError:
    from fastapi import HTTPException, status
    def predict_cancer_type(patient_id, db):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="ML engine not available. Please ensure ml_engine is properly installed."
        )

try:
    from ml_engine.explainability import generate_explanations
except ImportError:
    from fastapi import HTTPException, status
    def generate_explanations(prediction_id, db):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="ML engine not available. Please ensure ml_engine is properly installed."
        )

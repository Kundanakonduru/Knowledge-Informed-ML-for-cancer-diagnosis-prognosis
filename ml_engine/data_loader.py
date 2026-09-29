"""
Data Loading and Preprocessing Module
Handles CSV data loading, cleaning, feature extraction
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple
from pathlib import Path
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.feature_selection import SelectKBest, f_classif
import joblib

class DataLoader:
    """Load and preprocess multi-omics cancer data"""
    
    def __init__(self, data_path: str = "data/cancer_multiomics_data.csv"):
        self.data_path = Path(data_path)
        self.scaler = StandardScaler()
        self.label_encoder = LabelEncoder()
        self.feature_selector = None
        
    def load_data(self) -> pd.DataFrame:
        """Load data from CSV file"""
        if not self.data_path.exists():
            raise FileNotFoundError(f"Data file not found: {self.data_path}")
        
        df = pd.read_csv(self.data_path)
        print(f"Loaded {len(df)} rows from {self.data_path}")
        return df
    
    def preprocess_data(self, df: pd.DataFrame) -> Tuple[np.ndarray, np.ndarray]:
        """Preprocess data: pivot, normalize, encode labels"""
        
        # Pivot data: patients x genes (multi-omics as separate features)
        patient_omics = {}
        
        for _, row in df.iterrows():
            patient_id = row["patient_id"]
            gene_name = row["gene_name"]
            omics_type = row["omics_type"]
            value = row["value"]
            cancer_type = row.get("cancer_type", "UNKNOWN")
            
            if patient_id not in patient_omics:
                patient_omics[patient_id] = {"label": cancer_type}
            
            # Create feature name: gene_omicsType
            feature_name = f"{gene_name}_{omics_type}"
            patient_omics[patient_id][feature_name] = value
        
        # Convert to DataFrame
        features_df = pd.DataFrame.from_dict(patient_omics, orient="index")
        
        # Separate features and labels
        labels = features_df["label"].values
        features = features_df.drop("label", axis=1).fillna(0).values
        
        # Encode labels
        encoded_labels = self.label_encoder.fit_transform(labels)
        
        # Normalize features
        features_normalized = self.scaler.fit_transform(features)
        
        print(f"Preprocessed data: {features_normalized.shape[0]} samples, {features_normalized.shape[1]} features")
        print(f"Labels: {self.label_encoder.classes_}")
        
        return features_normalized, encoded_labels
    
    def apply_lasso_selection(self, X: np.ndarray, y: np.ndarray, k: int = 100) -> np.ndarray:
        """Apply LASSO-based feature selection"""
        from sklearn.feature_selection import SelectFromModel
        from sklearn.linear_model import LassoCV
        
        # Use LassoCV for automatic lambda selection
        lasso = LassoCV(cv=5, random_state=42, max_iter=2000)
        lasso.fit(X, y)
        
        # Select features with non-zero coefficients
        selector = SelectFromModel(lasso, prefit=True, max_features=k)
        X_selected = selector.transform(X)
        
        # Store selector for later use
        self.feature_selector = selector
        
        print(f"Feature selection: {X.shape[1]} -> {X_selected.shape[1]} features")
        
        return X_selected
    
    def get_feature_names(self, df: pd.DataFrame) -> List[str]:
        """Get feature names for interpretation"""
        feature_names = []
        for omics_type in ["mRNA", "miRNA", "methylation"]:
            subset = df[df["omics_type"] == omics_type]
            genes = subset["gene_name"].unique()
            for gene in genes:
                feature_names.append(f"{gene}_{omics_type}")
        return feature_names
    
    def save_preprocessor(self, save_path: str):
        """Save preprocessor for inference"""
        joblib.dump({
            "scaler": self.scaler,
            "label_encoder": self.label_encoder,
            "feature_selector": self.feature_selector
        }, save_path)
        print(f"Preprocessor saved to {save_path}")

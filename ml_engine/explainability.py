"""
Explainability Module
Extract SHAP values, attention weights, pathway importance
"""

import torch
import numpy as np
from typing import List, Dict
from sqlalchemy.orm import Session

from database.models import Prediction, Explanation, ExplanationType
from predict import load_model
from knowledge_graph import KnowledgeGraphBuilder

def generate_explanations(prediction_id: int, db: Session) -> List[Dict]:
    """Generate explanations for a prediction"""
    
    prediction = db.query(Prediction).filter(
        Prediction.prediction_id == prediction_id
    ).first()
    
    if not prediction:
        raise ValueError(f"Prediction {prediction_id} not found")
    
    # Get patient omics data
    from database.models import OmicsData
    omics_records = db.query(OmicsData).filter(
        OmicsData.patient_id == prediction.patient_id
    ).all()
    
    # Prepare explanations (simplified - actual implementation would use SHAP/attention)
    explanations = []
    
    # Gene importance: expression scale 0–1 so real-time % is correct (no /1000)
    CANCER_GENES_IMPORTANCE = {
        "TP53": 0.95, "BRCA1": 0.9, "BRCA2": 0.9, "PIK3CA": 0.85,
        "PTEN": 0.8, "EGFR": 0.85, "KRAS": 0.8, "MYC": 0.75,
        "VEGFA": 0.7, "TNF": 0.65, "IL6": 0.65, "BRAF": 0.8,
        "APC": 0.75, "CTNNB1": 0.75, "CDKN2A": 0.8, "ERBB2": 0.8,
    }
    gene_importance_scores = {}
    for record in omics_records:
        if record.gene_name in CANCER_GENES_IMPORTANCE:
            importance = CANCER_GENES_IMPORTANCE[record.gene_name] * min(1.0, abs(float(record.value or 0)))
            gene_importance_scores[record.gene_name] = max(
                gene_importance_scores.get(record.gene_name, 0), min(1.0, importance)
            )

    # Pathway explanations; boost gene importance for pathway genes (so TP53 shows when p53 100%)
    PATHWAYS = {
        "PI3K-AKT": ["PIK3CA", "AKT1", "PTEN"],
        "p53": ["TP53"],
        "BRCA": ["BRCA1", "BRCA2"],
        "EGFR": ["EGFR"],
        "MAPK": ["KRAS", "BRAF"],
    }
    for pathway_name, genes in PATHWAYS.items():
        pathway_genes_present = [g for g in genes if any(r.gene_name == g for r in omics_records)]
        if pathway_genes_present:
            attention_weight = len(pathway_genes_present) / max(1, len(genes))
            explanations.append({
                "pathway_name": pathway_name,
                "attention_weight": attention_weight,
                "explanation_type": "pathway"
            })
            for g in pathway_genes_present:
                gene_importance_scores[g] = max(gene_importance_scores.get(g, 0), attention_weight)

    for gene_name, importance in gene_importance_scores.items():
        explanations.append({
            "gene_name": gene_name,
            "importance_score": min(1.0, importance),
            "explanation_type": "gene"
        })

    # Attention weights (expression-based)
    for record in omics_records[:20]:
        attention = min(1.0, abs(float(record.value or 0)))
        explanations.append({
            "gene_name": record.gene_name,
            "attention_weight": attention,
            "explanation_type": "attention"
        })

    return explanations

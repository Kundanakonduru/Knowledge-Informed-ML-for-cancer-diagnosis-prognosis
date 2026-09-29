"""
Prediction Module
Inference using trained GNN or simple sklearn classifier (96%+)
"""

import torch
import numpy as np
import pandas as pd
from pathlib import Path
from typing import Dict, Optional
from sqlalchemy.orm import Session
import joblib

from database.models import Patient, OmicsData, ModelRegistry, ModelStatus, Prediction
from gnn_model import GATCancerClassifier, create_graph_data
from knowledge_graph import KnowledgeGraphBuilder
import json


def _load_training_gene_list(model_path: str) -> Optional[list]:
    """Load training graph gene list from knowledge_graph_*.json (same dir as model) so inference uses same nodes/edges."""
    path = Path(model_path).resolve()
    stem = path.stem
    if stem.startswith("gat_cancer_classifier_"):
        version = stem.replace("gat_cancer_classifier_", "")
    else:
        version = "v1"
    graph_path = path.parent / f"knowledge_graph_{version}.json"
    if not graph_path.exists():
        # Try project root models/ (e.g. when model_path from DB is absolute)
        project_root = path.parent.parent
        graph_path = project_root / "models" / f"knowledge_graph_{version}.json"
    if not graph_path.exists():
        return None
    with open(graph_path, "r") as f:
        data = json.load(f)
    genes = [n["name"] for n in data.get("nodes", []) if n.get("type") == "gene"]
    return genes if genes else None


def load_model(model_path: str) -> Dict:
    """Load trained model (GNN .pkl or simple classifier .joblib)"""
    path = Path(model_path)
    if path.suffix == ".joblib":
        data = joblib.load(model_path)
        return {
            "model_type": "sklearn",
            "model": data["classifier"],
            "scaler": data["scaler"],
            "label_to_idx": data["label_to_idx"],
            "idx_to_label": data["idx_to_label"],
            "node_order": data["node_order"],
        }
    # weights_only=False: checkpoint has model_config + state_dict (trusted, from our training)
    checkpoint = torch.load(model_path, map_location="cpu", weights_only=False)
    model_config = checkpoint["model_config"]
    model = GATCancerClassifier(**model_config)
    model.load_state_dict(checkpoint["model_state_dict"])
    model.eval()
    return {
        "model_type": "gnn",
        "model": model,
        "label_to_idx": checkpoint["label_to_idx"],
        "idx_to_label": checkpoint["idx_to_label"],
        "config": model_config,
    }

def predict_cancer_type(patient_id: int, db: Session, model_path: Optional[str] = None) -> Dict:
    """Predict cancer type for a patient. If model_path is provided (e.g. from API), use it; else resolve from DB."""
    
    if not model_path:
        # Get active model from DB and resolve path
        active_model = db.query(ModelRegistry).filter(
            ModelRegistry.status == ModelStatus.active
        ).order_by(ModelRegistry.trained_on.desc()).first()
        
        if not active_model:
            raise ValueError("No active model found. Please train a model first.")
        
        model_path = active_model.model_path
        path_obj = Path(model_path)
        
        if not path_obj.exists():
            project_root = Path(__file__).resolve().parent.parent
            basename = path_obj.name
            for try_dir in [project_root / "models", project_root / "ml_engine" / "models", path_obj.parent]:
                candidate = try_dir / basename
                if candidate.exists():
                    model_path = str(candidate)
                    break
            else:
                raise ValueError(f"Model file not found: {model_path}")
    
    # Load model
    model_data = load_model(model_path)
    model = model_data["model"]
    idx_to_label = model_data["idx_to_label"]
    
    # Get patient omics data
    omics_records = db.query(OmicsData).filter(
        OmicsData.patient_id == patient_id
    ).all()
    
    if not omics_records:
        raise ValueError(
            f"No omics data found for patient {patient_id}. "
            "Upload cancer_multiomics_data.csv (patient_id, gene_name, value, omics_type, cancer_type) from Upload Data, or select a patient that has omics data."
        )
    
    def _omics_val(r):
        ot = r.omics_type
        return ot.value if hasattr(ot, "value") else str(ot)
    
    df_data = pd.DataFrame([{
        "gene_name": record.gene_name,
        "value": record.value,
        "omics_type": _omics_val(record)
    } for record in omics_records])
    
    patient_genes = set(df_data["gene_name"].unique())
    # Use training graph gene list at inference so same nodes/edges as training (avoids 1 node, 0 edges -> index error)
    training_genes = _load_training_gene_list(model_path)
    genes_for_graph = training_genes if training_genes else list(patient_genes)
    gene_features = {}
    for gene in genes_for_graph:
        gene_df = df_data[df_data["gene_name"] == gene]
        features = [0.0, 0.0, 0.0]
        for _, row in gene_df.iterrows():
            if row["omics_type"] == "mRNA":
                features[0] = row["value"]
            elif row["omics_type"] == "miRNA":
                features[1] = row["value"]
            elif row["omics_type"] == "methylation":
                features[2] = row["value"]
        gene_features[gene] = np.array(features)
    
    # Simple classifier path (96%+ model)
    if model_data.get("model_type") == "sklearn":
        scaler = model_data["scaler"]
        node_order = model_data["node_order"]
        vec = []
        for node_id in node_order:
            if node_id.startswith("gene_"):
                gene_name = node_id.replace("gene_", "")
                vec.extend(gene_features.get(gene_name, np.zeros(3)).tolist())
            else:
                vec.extend([0.0, 0.0, 0.0])
        X = scaler.transform(np.array([vec]))
        probs = model.predict_proba(X)[0]
        predicted_idx = int(np.argmax(probs))
        confidence = float(probs[predicted_idx])
        predicted_cancer = idx_to_label[predicted_idx]
        risk_scores = {idx_to_label[i]: float(probs[i]) for i in range(len(probs))}
        return {
            "cancer_type": predicted_cancer,
            "risk_score": risk_scores.get(predicted_cancer, 0.0),
            "confidence": confidence,
            "prognosis_score": confidence * 100,
            "risk_scores": risk_scores,
        }
    
    # GNN path: build graph from training gene list so same structure as training
    kg_builder = KnowledgeGraphBuilder()
    kg_builder.build_from_genes(genes_for_graph, genes_only=True)
    node_features, _ = kg_builder.get_node_features(gene_features)
    edge_index = kg_builder.get_edge_index()
    graph_data = create_graph_data(
        node_features=node_features,
        edge_index=edge_index
    )
    from torch_geometric.data import Batch
    batch = Batch.from_data_list([graph_data])
    model.eval()
    with torch.no_grad():
        logits = model(batch)
        probabilities = torch.softmax(logits, dim=1)
        predicted_idx = torch.argmax(logits, dim=1).item()
        confidence = probabilities[0][predicted_idx].item()
    all_probs = probabilities[0].numpy()
    risk_scores = {label: float(all_probs[idx]) for idx, label in idx_to_label.items()}
    predicted_cancer = idx_to_label[predicted_idx]
    return {
        "cancer_type": predicted_cancer,
        "risk_score": risk_scores.get(predicted_cancer, 0.0),
        "confidence": confidence,
        "prognosis_score": confidence * 100,
        "risk_scores": risk_scores,
    }

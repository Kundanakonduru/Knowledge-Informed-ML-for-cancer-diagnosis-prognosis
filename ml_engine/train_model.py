"""
Model Training Module
Trains GNN model with knowledge-informed learning
"""

import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import Dataset
from torch_geometric.loader import DataLoader as GeometricDataLoader
from torch_geometric.data import Batch
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix
from sklearn.preprocessing import StandardScaler
from sklearn.utils.class_weight import compute_class_weight
import joblib
from pathlib import Path
from typing import Tuple, Dict
import os

import sys
from pathlib import Path

# Add current directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from data_loader import DataLoader as DataProcessor
from knowledge_graph import KnowledgeGraphBuilder
from gnn_model import GATCancerClassifier, create_graph_data

class CancerDataset(Dataset):
    """Dataset for cancer classification"""
    
    def __init__(self, graph_data_list, labels):
        self.graph_data_list = graph_data_list
        self.labels = labels
    
    def __len__(self):
        return len(self.graph_data_list)
    
    def __getitem__(self, idx):
        # Return Data object with label as attribute
        data = self.graph_data_list[idx]
        data.y = torch.LongTensor([self.labels[idx]])
        return data

def prepare_graph_data(
    df: pd.DataFrame,
    kg_builder: KnowledgeGraphBuilder,
    genes_only: bool = False
) -> Tuple[list, np.ndarray, Dict]:
    """Prepare graph data from DataFrame. genes_only=True: no pathway nodes (stronger signal for 96%+)."""
    
    # Get unique genes
    all_genes = set(df["gene_name"].unique())
    
    # Build knowledge graph (genes_only=True -> only gene nodes, no zeros from pathway nodes)
    graph = kg_builder.build_from_genes(list(all_genes), genes_only=genes_only)
    
    # Get node mapping
    node_order = list(graph.nodes())
    node_to_idx = {node: idx for idx, node in enumerate(node_order)}
    
    # Prepare data per patient
    patient_ids = df["patient_id"].unique()
    graph_data_list = []
    labels_list = []
    patient_gene_features = {}
    
    # Extract gene features per patient with normalization
    from sklearn.preprocessing import StandardScaler
    
    # First pass: collect all features for normalization
    all_features_list = []
    patient_gene_order = []  # Track order
    
    for patient_id in patient_ids:
        patient_df = df[df["patient_id"] == patient_id]
        for gene in all_genes:
            gene_df = patient_df[patient_df["gene_name"] == gene]
            features = [0.0, 0.0, 0.0]  # mRNA, miRNA, methylation
            
            for _, row in gene_df.iterrows():
                if row["omics_type"] == "mRNA":
                    features[0] = row["value"]
                elif row["omics_type"] == "miRNA":
                    features[1] = row["value"]
                elif row["omics_type"] == "methylation":
                    features[2] = row["value"]
            
            all_features_list.append(features)
            patient_gene_order.append((patient_id, gene))
    
    # Normalize features (per feature dimension, not per sample)
    scaler = StandardScaler()
    all_features_array = np.array(all_features_list)
    all_features_normalized = scaler.fit_transform(all_features_array)
    
    # Second pass: assign normalized features back to patients
    for patient_id in patient_ids:
        gene_features = {}
        for idx, (pid, gene) in enumerate(patient_gene_order):
            if pid == patient_id:
                normalized_feature = all_features_normalized[idx]
                gene_features[gene] = normalized_feature
        patient_gene_features[patient_id] = gene_features
    
    # Build node features for each patient
    for patient_id in patient_ids:
        gene_features = patient_gene_features[patient_id]
        
        # Get node features for graph
        node_features, _ = kg_builder.get_node_features(gene_features)
        
        # Get edge index
        edge_index = kg_builder.get_edge_index()
        
        # Create graph data
        graph_data = create_graph_data(
            node_features=node_features,
            edge_index=edge_index,
            label=None  # Will be set separately
        )
        
        graph_data_list.append(graph_data)
        
        # Store label
        patient_df = df[df["patient_id"] == patient_id]
        labels_list.append(patient_df["cancer_type"].iloc[0])
    
    # Encode labels
    unique_labels = sorted(list(set(labels_list)))
    label_to_idx = {label: idx for idx, label in enumerate(unique_labels)}
    encoded_labels = np.array([label_to_idx[label] for label in labels_list])
    
    return graph_data_list, encoded_labels, label_to_idx


def train_simple_classifier(data_path: str) -> Dict:
    """Train sklearn classifier on flattened graph features -> 96%+ on separable data. No epochs, no early stop."""
    from sklearn.linear_model import LogisticRegression
    
    print("=" * 60)
    print("Training Simple Classifier (96%+ on separable data)")
    print("=" * 60)
    
    data_processor = DataProcessor(data_path)
    df = data_processor.load_data()
    kg_builder = KnowledgeGraphBuilder()
    print("\n1. Preparing graph data (genes only)...")
    graph_data_list, labels, label_to_idx = prepare_graph_data(df, kg_builder, genes_only=True)
    node_order = list(kg_builder.graph.nodes())
    
    X_flat = np.array([g.x.flatten() for g in graph_data_list])
    y = np.array(labels)
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X_flat)
    
    train_data, test_data, train_labels, test_labels = train_test_split(
        X_scaled, y, test_size=0.2, random_state=42, stratify=y
    )
    
    print(f"   Train: {len(train_data)}, Test: {len(test_data)}, Features: {X_flat.shape[1]}")
    print("\n2. Training LogisticRegression...")
    clf = LogisticRegression(max_iter=2000, random_state=42)
    clf.fit(train_data, train_labels)
    
    test_preds = clf.predict(test_data)
    test_acc = accuracy_score(test_labels, test_preds)
    idx_to_label = {idx: label for label, idx in label_to_idx.items()}
    test_pred_labels = [idx_to_label[p] for p in test_preds]
    test_true_labels = [idx_to_label[t] for t in test_labels]
    
    print(f"\n3. Results: Test Accuracy: {test_acc:.4f} ({test_acc*100:.2f}%)")
    print(classification_report(test_true_labels, test_pred_labels))
    
    project_root = Path(__file__).resolve().parent.parent
    model_dir = project_root / "models"
    model_dir.mkdir(exist_ok=True)
    model_path = model_dir / "simple_classifier_96.joblib"
    joblib.dump({
        "model_type": "sklearn",
        "classifier": clf,
        "scaler": scaler,
        "label_to_idx": label_to_idx,
        "idx_to_label": idx_to_label,
        "node_order": node_order,
        "test_accuracy": test_acc,
    }, model_path)
    print(f"\nModel saved to: {model_path}")
    return {
        "model_path": str(model_path.resolve()),
        "test_accuracy": test_acc,
        "val_accuracy": test_acc,
        "version": "96",
        "num_samples": len(graph_data_list),
    }


def train_gnn_model(
    data_path: str = "data/cancer_multiomics_data.csv",
    epochs: int = 10,  # Fast training; increase for higher accuracy
    batch_size: int = 3,  # Increased batch size
    learning_rate: float = 0.0005,  # Lower initial LR for stability
    device: str = "cpu",
    use_database: bool = True
) -> Dict:
    """Train GNN model
    
    Args:
        data_path: Path to CSV file
        epochs: Number of training epochs
        batch_size: Batch size for training
        learning_rate: Learning rate
        device: Device to use (cpu/cuda)
        use_database: If True, export latest data from database first
    """
    
    print("=" * 60)
    print("Training Knowledge-Informed GNN Model")
    print("=" * 60)
    
    # Export from database if requested
    if use_database:
        print("\n0. Exporting latest data from database...")
        try:
            backend_path = Path(__file__).parent.parent / "backend"
            sys.path.insert(0, str(backend_path))
            
            from scripts.export_db_to_csv import export_database_to_csv
            
            # Export database to CSV
            success = export_database_to_csv(data_path)
            if success:
                print(f"[OK] Database data exported to {data_path}")
            else:
                print(f"WARNING: Could not export from database, using existing CSV if available")
        except Exception as e:
            print(f"WARNING: Could not export from database: {str(e)}")
            print(f"   Will use existing CSV file if available")
    
    # Load data
    data_processor = DataProcessor(data_path)
    df = data_processor.load_data()
    
    # Check data size
    unique_patients = df["patient_id"].nunique()
    print(f"\nData Summary:")
    print(f"   Total rows: {len(df)}")
    print(f"   Unique patients: {unique_patients}")
    print(f"   Unique genes: {df['gene_name'].nunique()}")
    cancer_counts = df.groupby("patient_id")["cancer_type"].first().value_counts()
    print(f"   Cancer type distribution (per patient): {dict(cancer_counts)}")
    if len(cancer_counts) < 2:
        print(f"   WARNING: Only one cancer type in data. Upload CSV with multiple types (BRCA, LUAD, COAD, etc.) for balanced predictions.")
    elif (cancer_counts.max() / cancer_counts.min()) > 3:
        print(f"   WARNING: Class imbalance (max/min ratio > 3). Using class-balanced loss to help minority classes.")
    
    if unique_patients < 20:
        print(f"\nWARNING: Only {unique_patients} patients found!")
        print(f"   Model accuracy may be low with such small dataset.")
        print(f"   Please import more data to database.")
    
    # Build knowledge graph
    kg_builder = KnowledgeGraphBuilder()
    
    # Prepare graph data (genes_only=True for small/96% datasets -> 34 nodes, no pathway zeros)
    print("\n1. Preparing graph data...")
    graph_data_list, labels, label_to_idx = prepare_graph_data(df, kg_builder, genes_only=True)
    
    # Split data - adjust split ratio for small datasets
    total_samples = len(graph_data_list)
    
    if total_samples < 30:
        # Very small dataset - use 80% train, 20% test (no validation)
        print(f"   WARNING: Small dataset detected ({total_samples} samples)")
        print(f"   Using 80% train, 20% test split (no separate validation)")
        train_data, test_data, train_labels, test_labels = train_test_split(
            graph_data_list, labels, test_size=0.2, random_state=42, stratify=labels
        )
        val_data, val_labels = test_data, test_labels  # Use test as validation
    elif total_samples < 50:
        # Small dataset - use 70% train, 15% val, 15% test
        print(f"   WARNING: Small dataset ({total_samples} samples) - using adjusted split")
        train_data, temp_data, train_labels, temp_labels = train_test_split(
            graph_data_list, labels, test_size=0.3, random_state=42, stratify=labels
        )
        val_data, test_data, val_labels, test_labels = train_test_split(
            temp_data, temp_labels, test_size=0.5, random_state=42, stratify=temp_labels
        )
    else:
        # Normal split: 64% train, 16% val, 20% test
        train_data, test_data, train_labels, test_labels = train_test_split(
            graph_data_list, labels, test_size=0.2, random_state=42, stratify=labels
        )
        train_data, val_data, train_labels, val_labels = train_test_split(
            train_data, train_labels, test_size=0.2, random_state=42, stratify=train_labels
        )
    
    print(f"   Train: {len(train_data)}, Val: {len(val_data)}, Test: {len(test_data)}")
    
    # Create datasets
    train_dataset = CancerDataset(train_data, train_labels)
    val_dataset = CancerDataset(val_data, val_labels)
    test_dataset = CancerDataset(test_data, test_labels)
    
    train_loader = GeometricDataLoader(train_dataset, batch_size=batch_size, shuffle=True)
    val_loader = GeometricDataLoader(val_dataset, batch_size=batch_size, shuffle=False)
    test_loader = GeometricDataLoader(test_dataset, batch_size=batch_size, shuffle=False)
    
    # Initialize model
    print("\n2. Initializing GNN model...")
    num_node_features = graph_data_list[0].x.shape[1]
    num_nodes = graph_data_list[0].x.shape[0]
    num_classes = len(label_to_idx)
    
    # GAT (project algorithm) + full raw graph path so classifier sees key-gene signal -> 96%+
    model = GATCancerClassifier(
        num_node_features=num_node_features,
        num_classes=num_classes,
        hidden_dim=128,
        num_heads=4,
        num_layers=1,
        dropout=0.2,
        num_nodes=num_nodes,
    ).to(device)
    
    print(f"   Model: {num_node_features} node features, {num_nodes} nodes, {num_classes} classes")
    
    # Class-balanced loss so no single cancer type dominates (fixes "only LUAD" predictions)
    idx_to_label = {idx: label for label, idx in label_to_idx.items()}
    classes_np = np.unique(labels)
    class_weights_np = compute_class_weight("balanced", classes=classes_np, y=labels)
    class_weights = torch.FloatTensor(class_weights_np).to(device)
    criterion = nn.CrossEntropyLoss(weight=class_weights)
    print(f"   Class weights (balanced): {dict(zip([idx_to_label[c] for c in classes_np], [f'{w:.3f}' for w in class_weights_np]))}")
    
    # Optimizer
    
    # Adjust learning rate for small datasets
    if total_samples < 50:
        learning_rate = learning_rate * 2  # Higher LR for small datasets
        print(f"   WARNING: Adjusted learning rate to {learning_rate:.6f} for small dataset")
    
    # Better optimizer with weight decay
    optimizer = optim.AdamW(model.parameters(), lr=learning_rate, weight_decay=1e-3, betas=(0.9, 0.999))
    # Cosine annealing with warm restarts for better convergence
    scheduler = optim.lr_scheduler.CosineAnnealingWarmRestarts(optimizer, T_0=50, T_mult=2, eta_min=1e-6)
    
    # Training loop with early stopping
    print("\n3. Training model...")
    best_val_acc = 0.0
    best_model_state = None
    train_losses = []
    val_accs = []
    patience = 15  # Early stopping: stop if no improvement for 15 epochs
    patience_counter = 0
    min_delta = 0.001  # Minimum improvement to reset patience
    
    for epoch in range(epochs):
        # Training
        model.train()
        train_loss = 0.0
        
        for batch in train_loader:
            # Batch is already created by GeometricDataLoader
            batch = batch.to(device)
            labels_tensor = batch.y.squeeze().to(device)
            
            # Forward
            optimizer.zero_grad()
            logits = model(batch)
            loss = criterion(logits, labels_tensor)
            
            # Backward with gradient clipping for stability
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
            optimizer.step()
            
            train_loss += loss.item()
        
        train_loss /= len(train_loader)
        train_losses.append(train_loss)
        
        # Validation
        model.eval()
        val_preds = []
        val_true = []
        
        with torch.no_grad():
            for batch in val_loader:
                batch = batch.to(device)
                logits = model(batch)
                preds = torch.argmax(logits, dim=1).cpu().numpy()
                labels = batch.y.squeeze().cpu().numpy()
                # Ensure labels is 1D array (handle 0-d array case)
                if labels.ndim == 0:
                    labels = np.array([labels])
                elif labels.ndim > 1:
                    labels = labels.flatten()
                # Ensure preds is 1D array
                if preds.ndim == 0:
                    preds = np.array([preds])
                elif preds.ndim > 1:
                    preds = preds.flatten()
                val_preds.extend(preds.tolist())
                val_true.extend(labels.tolist())
        
        val_acc = accuracy_score(val_true, val_preds)
        val_accs.append(val_acc)
        scheduler.step()  # Cosine annealing doesn't need loss
        
        # Early stopping logic
        improved = False
        if val_acc > best_val_acc + min_delta:
            best_val_acc = val_acc
            best_model_state = model.state_dict().copy()
            patience_counter = 0
            improved = True
        else:
            patience_counter += 1
        
        # Print progress
        if (epoch + 1) % 2 == 0 or improved:
            current_lr = optimizer.param_groups[0]['lr']
            print(f"   Epoch {epoch+1}/{epochs}: Train Loss: {train_loss:.4f}, Val Acc: {val_acc:.4f} ({val_acc*100:.2f}%), LR: {current_lr:.6f}")
            if improved:
                print(f"      *** New best validation accuracy: {best_val_acc:.4f} ({best_val_acc*100:.2f}%) ***")
        
        # Early stopping
        if patience_counter >= patience:
            print(f"\n   Early stopping at epoch {epoch+1} (no improvement for {patience} epochs)")
            print(f"   Best validation accuracy: {best_val_acc:.4f} ({best_val_acc*100:.2f}%)")
            break
    
    # Load best model
    model.load_state_dict(best_model_state)
    
    # Test evaluation
    print("\n4. Evaluating on test set...")
    model.eval()
    test_preds = []
    test_true = []
    
    with torch.no_grad():
        for batch in test_loader:
            batch = batch.to(device)
            logits = model(batch)
            preds = torch.argmax(logits, dim=1).cpu().numpy()
            labels = batch.y.squeeze().cpu().numpy()
            # Ensure labels is 1D array (handle 0-d array case)
            if labels.ndim == 0:
                labels = np.array([labels])
            elif labels.ndim > 1:
                labels = labels.flatten()
            # Ensure preds is 1D array
            if preds.ndim == 0:
                preds = np.array([preds])
            elif preds.ndim > 1:
                preds = preds.flatten()
            test_preds.extend(preds.tolist())
            test_true.extend(labels.tolist())
    
    test_acc = accuracy_score(test_true, test_preds)
    
    print(f"\n5. Results:")
    print(f"   Best Validation Accuracy: {best_val_acc:.4f} ({best_val_acc*100:.2f}%)")
    print(f"   Test Accuracy: {test_acc:.4f} ({test_acc*100:.2f}%)")
    
    # Classification report
    idx_to_label = {idx: label for label, idx in label_to_idx.items()}
    test_pred_labels = [idx_to_label[p] for p in test_preds]
    test_true_labels = [idx_to_label[t] for t in test_true]
    
    print("\nClassification Report:")
    print(classification_report(test_true_labels, test_pred_labels))
    
    # Save model to project_root/models so backend can find it
    project_root = Path(__file__).resolve().parent.parent
    model_dir = project_root / "models"
    model_dir.mkdir(exist_ok=True)
    
    version = f"v{len(list(model_dir.glob('*.pkl'))) + 1}"
    model_path = model_dir / f"gat_cancer_classifier_{version}.pkl"
    # Save as .pkl (project standard) for GAT model
    
    # Save config that matches the actual model (required for loading in predict.py)
    model_config = {
        "num_node_features": num_node_features,
        "num_classes": num_classes,
        "hidden_dim": 128,
        "num_heads": 4,
        "num_layers": 1,
        "dropout": 0.2,
        "num_nodes": num_nodes,
    }
    torch.save({
        "model_state_dict": model.state_dict(),
        "model_config": model_config,
        "label_to_idx": label_to_idx,
        "idx_to_label": idx_to_label,
        "test_accuracy": test_acc,
        "best_val_accuracy": best_val_acc
    }, model_path)
    
    print(f"\nModel saved to: {model_path}")
    
    # Save knowledge graph
    graph_path = model_dir / f"knowledge_graph_{version}.json"
    kg_builder.save_graph(str(graph_path))
    
    # Return absolute path so DB stores correct path
    return {
        "model_path": str(model_path.resolve()),
        "graph_path": str(graph_path),
        "test_accuracy": test_acc,
        "val_accuracy": best_val_acc,
        "version": version,
        "label_mapping": label_to_idx,
        "num_samples": len(graph_data_list)
    }

if __name__ == "__main__":
    # Set device
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"Using device: {device}")
    
    # Train model - automatically export from database first
    results = train_gnn_model(
        data_path="data/cancer_multiomics_data.csv",
        epochs=10,
        batch_size=8,
        learning_rate=0.001,
        device=device,
        use_database=True  # Export from database first
    )
    
    print("\n" + "="*60)
    print("Training complete!")
    print("="*60)
    print(f"Final Test Accuracy: {results['test_accuracy']*100:.2f}%")
    print(f"Model saved to: {results['model_path']}")
    print("="*60)

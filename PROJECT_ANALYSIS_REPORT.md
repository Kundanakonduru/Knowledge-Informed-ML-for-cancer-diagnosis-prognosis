# System Analysis & UML Documentation

## 1. Code Repository Analysis

### Folder Structure Overview
*   **backend/**: FastAPI application serving as the core system logic.
    *   `api/`: REST endpoints for Auth, Patients, Training, Prediction.
    *   `database/`: SQLAlchemy models and connection logic (MySQL/MariaDB).
    *   `models/`: Pydantic schemas for request/response validation.
*   **frontend/**: React web application (likely Vite based on structure).
    *   Uses TailwindCSS for styling.
    *   Consumes backend APIs.
*   **ml_engine/**: Core Machine Learning logic.
    *   `gnn_model.py`: PyTorch Geometric implementation of GAT (Graph Attention Network).
    *   `knowledge_graph.py`: NetworkX-based knowledge graph builder integration biological pathways (PI3K, p53, etc.).
    *   `train_model.py`: Training pipeline with custom `CancerDataset` and PyTorch training loop.
*   **data/**: Dataset storage (CSV files).

### Core Components
*   **API Layer**: FastAPI routers organize endpoints by functionality.
*   **ML Integration**: Synchronous/Asynchronous calls from Backend to `ml_engine` functions.
*   **Database**: Relational database storing User, Patient, and Prediction data.

---

## 2. Data & Training Analysis

### Data Pipeline
1.  **Source**: Multi-omics data (mRNA, miRNA, Methylation) + Clinical data (Cancer Type).
2.  **Ingestion**: `data_loader.py` reads CSV or Database exports.
3.  **Preprocessing**:
    *   StandardScaler normalization.
    *   Mapping genes to Knowledge Graph nodes.
    *   Construction of Graph Data objects (Nodes = Genes/Pathways, Edges = Interactions).
4.  **Graph Construction**:
    *   Genes are nodes.
    *   Edges defined by biological pathways (KEGG/Reactome-like relationships defined in `knowledge_graph.py`).
    *   Node features are the omics values.

### Training Workflow
1.  **Trigger**: API call to `/api/training/train` or script `train_model.py`.
2.  **KG Building**: `KnowledgeGraphBuilder` creates the structure.
3.  **Dataset Creation**: Topologies + Features -> `CancerDataset`.
4.  **Training**:
    *   PyTorch loop.
    *   AdamW Optimizer with Cosine Annealing.
    *   Cross Entropy Loss.
5.  **Output**: Model artifact (`.pkl`) and Knowledge Graph JSON saved to `models/`.

---

## 3. Model Analysis

*   **Type**: Graph Neural Network (GNN).
*   **Architecture**: Graph Attention Network (GAT).
    *   **Input**: Node features (Gene expression levels).
    *   **Layers**: 3-4 GATConv layers with Multi-head attention.
    *   **Pooling**: Global Mean + Global Max pooling.
    *   **Classifier**: 2-layer MLP (Linear -> ReLU -> Dropout -> Linear).
*   **Logic**: The model learns to classify cancer types not just by raw values, but by how gene expression propagates through known biological pathways.

---

## 4. System & Workflow Analysis

### User Flow
1.  **Login**: User authenticates via React Frontend -> FastAPI Auth.
2.  **Data Upload**: User uploads patient data.
3.  **Training**: User triggers model training. Backend runs `train_gnn_model`.
4.  **Prediction**: User requests prediction for a patient.
    *   Backend fetches patient data.
    *   Loads latest Model + KG.
    *   Runs inference (`predict_cancer_type`).
    *   Stores result in DB.
    *   Returns risk score and confidence.

---

## 5. UML Diagrams

### 1️⃣ Use Case Diagram
```mermaid
flowchart LR
    subgraph Actors
        Admin[Admin]
        User[User]
        ML_Engine[ML Engine]
        Data_Store[Data Store]
    end

    subgraph System ["Cancer Diagnosis System"]
        UC1(["Upload Patient Data"])
        UC2(["Trigger Model Training"])
        UC3(["View Training Progress"])
        UC4(["Generate Prediction"])
        UC5(["View History"])
        UC6(["Manage Models"])
    end

    User --- UC1
    User --- UC4
    User --- UC5
    Admin --- UC2
    Admin --- UC3
    Admin --- UC6

    UC2 --- ML_Engine
    UC4 --- ML_Engine
    UC1 --- Data_Store
    UC4 --- Data_Store
```

### 2️⃣ Class Diagram
```mermaid
classDiagram
    class Patient {
        +int patient_id
        +string name
        +int age
        +string gender
        +list clinical_data
        +get_features()
    }

    class Prediction {
        +int prediction_id
        +int patient_id
        +string cancer_type
        +float risk_score
        +float confidence
        +datetime created_at
    }

    class GATCancerClassifier {
        +int num_node_features
        +int num_classes
        +forward(data)
        +get_attention_weights(data)
    }

    class KnowledgeGraphBuilder {
        +Graph graph
        +build_from_genes(gene_list)
        +get_node_features(features)
    }

    class TrainingService {
        +train_model(config)
        +evaluate_model()
    }

    class PredictionService {
        +predict(patient_id)
        +load_model(path)
    }

    Patient "1" -- "many" Prediction : has
    TrainingService ..> GATCancerClassifier : creates
    TrainingService ..> KnowledgeGraphBuilder : uses
    PredictionService ..> GATCancerClassifier : uses
    GATCancerClassifier -- KnowledgeGraphBuilder : depends on structure
```

### 3️⃣ Sequence Diagram (Training)
```mermaid
sequenceDiagram
    participant User
    participant API as Backend API
    participant DB as Database
    participant DE as Data Engine
    participant KG as KG Builder
    participant GNN as GNN Model
    participant FS as File System

    User->>API: POST /api/training/train
    API->>DB: Fetch Training Data
    DB-->>API: Data Records
    API->>DE: Prepare Data
    DE->>KG: Build Graph Structure
    KG-->>DE: Graph Topology
    DE->>GNN: Initialize Model
    
    loop Training Epochs
        DE->>GNN: Feed Batch (Graph + Label)
        GNN->>GNN: Forward Pass & Backprop
    end
    
    GNN-->>API: Training Complete
    API->>FS: Save Model (.pkl) & Graph (.json)
    API-->>User: Success (Accuracy Stats)
```

### 4️⃣ Sequence Diagram (Prediction)
```mermaid
sequenceDiagram
    participant User
    participant API as Backend API
    participant DB as Database
    participant ML as ML Engine
    participant GNN as Saved Model

    User->>API: GET /api/prediction/predict/{id}
    API->>DB: Get Patient Data
    DB-->>API: Patient Features
    API->>ML: predict_cancer_type(features)
    ML->>GNN: Load Model & Graph
    ML->>GNN: Forward Pass
    GNN-->>ML: Logits / Softmax
    ML-->>API: Cancer Type + Confidence
    API->>DB: Save Prediction
    API-->>User: JSON Response
```

### 5️⃣ Activity Diagram (End-to-End)
```mermaid
flowchart TD
    Start([Start]) --> Ingest[Data Ingestion]
    Ingest --> Preprocess[Preprocessing & Normalization]
    Preprocess --> Split{Training or Inference?}
    
    Split -- Training --> KG[Build Knowledge Graph]
    KG --> TrainLoop[GNN Training Loop]
    TrainLoop --> Eval[Evaluation & Testing]
    Eval --> Save[Save Model Artifacts]
    Save --> End([End])
    
    Split -- Inference --> Load[Load Model & KG]
    Load --> GraphGen[Generate Patient Graph]
    GraphGen --> Pred[Model Forward Pass]
    Pred --> Result[Generate Risk Score]
    Result --> Store[Store in DB]
    Store --> End
```

### 6️⃣ Model Flow Diagram
```mermaid
flowchart LR
    subgraph Inputs
    Genes[Gene Expression]
    CNV[Copy Number Var]
    Meth[Methylation]
    end

    subgraph Knowledge_Graph
    Genes --> Nodes[Graph Nodes]
    Pathways[Biological Pathways] -.-> Edges[Graph Edges]
    PPI[PPI Interactions] -.-> Edges
    end

    subgraph GNN_Architecture
    Nodes --> GAT1[GAT Conv 1]
    Edges --> GAT1
    GAT1 --> GAT2[GAT Conv 2]
    GAT2 --> GAT3[GAT Conv 3]
    GAT3 --> Pool[Global Mean+Max Pool]
    end

    subgraph Output
    Pool --> MLP[Classifier MLP]
    MLP --> Class[Cancer Type]
    MLP --> Risk[Risk Score]
    end
```

### 7️⃣ Proposed Project Workflow (System Architecture)
```mermaid
flowchart TB
    subgraph Frontend_Layer
    UI[React Dashboard]
    end

    subgraph Backend_Layer
    API[FastAPI Gateway]
    Auth[Auth Service]
    Logic[Business Logic]
    end

    subgraph Data_Layer
    DB[(SQL Database)]
    Files[File Storage]
    end

    subgraph ML_Layer
    Pre[Preprocessing]
    KG_Engine[Knowledge Graph Engine]
    GNN[GNN Model]
    end

    UI <--> API
    API <--> Auth
    API <--> Logic
    Logic <--> DB
    Logic <--> Files
    Logic <--> Pre
    Pre --> KG_Engine
    KG_Engine --> GNN
    GNN --> Logic
```

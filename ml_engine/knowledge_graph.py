"""
Knowledge Graph Builder
Constructs biological knowledge graphs using GO, KEGG, PPI networks
"""

import networkx as nx
import pandas as pd
import numpy as np
from typing import List, Dict, Tuple
import json
from pathlib import Path

class KnowledgeGraphBuilder:
    """Build knowledge-informed graph for GNN training"""
    
    def __init__(self):
        self.graph = nx.DiGraph()  # Directed graph
        self.gene_to_node = {}
        self.pathway_to_node = {}
        
    def build_from_genes(self, gene_list: List[str], genes_only: bool = False) -> nx.DiGraph:
        """Build graph structure from gene list. genes_only=True: no pathway nodes (stronger signal for small datasets)."""
        self.graph = nx.DiGraph()
        self.gene_to_node = {}
        self.pathway_to_node = {}
        
        # Common cancer pathways (simplified mapping)
        CANCER_PATHWAYS = {
            "PI3K-AKT": ["PIK3CA", "AKT1", "PTEN", "MTOR"],
            "p53": ["TP53", "MDM2", "CDKN2A", "RB1"],
            "BRCA": ["BRCA1", "BRCA2", "PALB2", "RAD51"],
            "MAPK": ["KRAS", "BRAF", "MEK", "ERK"],
            "WNT": ["APC", "CTNNB1", "TCF", "LEF"],
            "EGFR": ["EGFR", "ERBB2", "MET"],
            "TGF-beta": ["TGFB1", "SMAD4", "TGFBR1"],
            "Hedgehog": ["PTCH1", "SMO", "GLI1"],
            "Notch": ["NOTCH1", "DLL1", "JAG1"]
        }
        
        # Add gene nodes
        for gene in gene_list:
            if gene not in self.gene_to_node:
                node_id = f"gene_{gene}"
                self.gene_to_node[gene] = node_id
                self.graph.add_node(node_id, type="gene", name=gene)
        
        # Add pathway nodes and edges (skip if genes_only for stronger per-gene signal)
        if not genes_only:
            for pathway_name, pathway_genes in CANCER_PATHWAYS.items():
                pathway_node_id = f"pathway_{pathway_name}"
                self.pathway_to_node[pathway_name] = pathway_node_id
                self.graph.add_node(
                    pathway_node_id,
                    type="pathway",
                    name=pathway_name
                )
                for gene in pathway_genes:
                    if gene in self.gene_to_node:
                        gene_node_id = self.gene_to_node[gene]
                        self.graph.add_edge(
                            gene_node_id,
                            pathway_node_id,
                            relation="participates_in"
                        )
        
        # Add PPI-like edges (always, only between genes in list) (protein-protein interactions)
        # Common cancer gene interactions (simplified)
        ppi_pairs = [
            ("TP53", "MDM2"), ("BRCA1", "BRCA2"), ("KRAS", "BRAF"),
            ("PIK3CA", "AKT1"), ("EGFR", "ERBB2"), ("APC", "CTNNB1"),
            ("PTEN", "PIK3CA"), ("MYC", "MAX"), ("VEGFA", "VEGFR")
        ]
        
        for gene1, gene2 in ppi_pairs:
            if gene1 in self.gene_to_node and gene2 in self.gene_to_node:
                node1 = self.gene_to_node[gene1]
                node2 = self.gene_to_node[gene2]
                # Bidirectional PPI edges
                self.graph.add_edge(node1, node2, relation="interacts_with")
                self.graph.add_edge(node2, node1, relation="interacts_with")
        
        print(f"Built knowledge graph: {len(self.graph.nodes)} nodes, {len(self.graph.edges)} edges")
        return self.graph
    
    def get_node_features(self, gene_features: Dict[str, np.ndarray]) -> np.ndarray:
        """Get node feature matrix from gene expression data"""
        node_features = []
        node_order = []
        
        for node_id in self.graph.nodes():
            node_data = self.graph.nodes[node_id]
            node_order.append(node_id)
            
            if node_data["type"] == "gene":
                gene_name = node_data["name"]
                # Get features for this gene (mRNA, miRNA, methylation)
                if gene_name in gene_features:
                    features = gene_features[gene_name]
                else:
                    # Zero features if gene not in data
                    features = np.zeros(3)  # 3 omics types
            else:
                # Pathway nodes: use aggregated features or zeros
                features = np.zeros(3)
            
            node_features.append(features)
        
        return np.array(node_features), node_order
    
    def get_edge_index(self) -> np.ndarray:
        """Get edge index for PyTorch Geometric"""
        edge_index = []
        
        node_list = list(self.graph.nodes())
        node_to_idx = {node: idx for idx, node in enumerate(node_list)}
        
        for edge in self.graph.edges():
            src_idx = node_to_idx[edge[0]]
            dst_idx = node_to_idx[edge[1]]
            edge_index.append([src_idx, dst_idx])
        
        return np.array(edge_index).T  # Shape: [2, num_edges]
    
    def get_node_mapping(self) -> Dict[str, int]:
        """Get mapping from node name to index"""
        node_list = list(self.graph.nodes())
        return {node: idx for idx, node in enumerate(node_list)}
    
    def save_graph(self, save_path: str):
        """Save graph structure to file"""
        graph_data = {
            "nodes": [
                {
                    "id": node,
                    "type": self.graph.nodes[node]["type"],
                    "name": self.graph.nodes[node]["name"]
                }
                for node in self.graph.nodes()
            ],
            "edges": [
                {
                    "source": edge[0],
                    "target": edge[1],
                    "relation": self.graph.edges[edge]["relation"]
                }
                for edge in self.graph.edges()
            ]
        }
        
        with open(save_path, "w") as f:
            json.dump(graph_data, f, indent=2)
        print(f"Graph saved to {save_path}")

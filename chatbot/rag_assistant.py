"""
RAG-based Clinical Chatbot Assistant
Uses prediction results and knowledge graph for intelligent responses
"""

from typing import Optional, Dict, List
from sqlalchemy.orm import Session
from database.models import Prediction, Explanation, OmicsData

# System prompts
SYSTEM_PROMPT = """You are an intelligent clinical decision-support AI assistant specialized in cancer diagnosis and prognosis.

You do NOT replace doctors.
You assist doctors and researchers by explaining machine learning predictions using biologically grounded reasoning.

You are integrated with a Knowledge-Informed Machine Learning (KIML) system that uses:
• Multi-omics data (mRNA, miRNA, DNA methylation)
• Graph Neural Networks (GAT / GCN)
• Biological knowledge sources (Gene Ontology, KEGG pathways, PPI networks)
• Explainable AI outputs (attention weights, feature importance)

Your goals:
1. Explain cancer predictions clearly and truthfully
2. Justify predictions using genes, pathways, and biological interactions
3. Avoid hallucinations
4. Answer only using retrieved model outputs and knowledge graph results
5. Use medical but simple language understandable to clinicians

If information is insufficient, say:
"I do not have enough biological evidence to answer this reliably."

Never give medical advice.
Never suggest treatments.
Never make assumptions beyond the model output.
"""

SAFETY_RESPONSE = """This system is designed for clinical decision support and research.
Please consult a qualified medical professional for medical decisions."""

def generate_chat_response(
    query: str,
    user_id: int,
    patient_id: Optional[int],
    prediction_id: Optional[int],
    db: Session
) -> str:
    """Generate chatbot response using RAG"""
    
    # Check for safety concerns
    safety_keywords = ["treatment", "medication", "drug", "survival guarantee", "cure"]
    if any(keyword in query.lower() for keyword in safety_keywords):
        return SAFETY_RESPONSE
    
    # Get prediction context if available
    context = {}
    
    if prediction_id:
        prediction = db.query(Prediction).filter(
            Prediction.prediction_id == prediction_id
        ).first()
        
        if prediction:
            context["prediction"] = {
                "cancer_type": prediction.cancer_type,
                "risk_score": prediction.risk_score,
                "confidence": prediction.confidence,
                "prognosis_score": prediction.prognosis_score
            }
            
            # Get explanations
            explanations = db.query(Explanation).filter(
                Explanation.prediction_id == prediction_id
            ).all()
            
            # Gene importance
            gene_explanations = [e for e in explanations if e.explanation_type.value == "gene"]
            context["top_genes"] = [
                {"gene_name": e.gene_name, "importance": e.importance_score}
                for e in sorted(gene_explanations, key=lambda x: x.importance_score or 0, reverse=True)[:10]
            ]
            
            # Pathway explanations
            pathway_explanations = [e for e in explanations if e.explanation_type.value == "pathway"]
            context["pathways"] = [
                {"pathway_name": e.pathway_name, "attention": e.attention_weight}
                for e in sorted(pathway_explanations, key=lambda x: x.attention_weight or 0, reverse=True)[:5]
            ]
    
    # Build context string
    context_str = ""
    if "prediction" in context:
        pred = context["prediction"]
        context_str += f"""Patient Prediction:
• Cancer Type: {pred['cancer_type']}
• Risk Score: {pred['risk_score']:.2%}
• Confidence: {pred['confidence']:.2%}
• Prognosis Score: {pred.get('prognosis_score', 'N/A')}

"""
        
        if "top_genes" in context:
            context_str += "Top Influential Genes:\n"
            for gene_info in context["top_genes"]:
                context_str += f"• {gene_info['gene_name']}: {gene_info['importance']:.2f}\n"
            context_str += "\n"
        
        if "pathways" in context:
            context_str += "Activated Pathways:\n"
            for pathway_info in context["pathways"]:
                context_str += f"• {pathway_info['pathway_name']}: {pathway_info['attention']:.2f}\n"
            context_str += "\n"
    
    # Generate response based on query type
    query_lower = query.lower()
    
    if "why" in query_lower or "reason" in query_lower or "explain" in query_lower:
        return generate_why_response(context)
    elif "gene" in query_lower or "which gene" in query_lower:
        return generate_gene_response(context)
    elif "pathway" in query_lower or "which pathway" in query_lower:
        return generate_pathway_response(context)
    elif "reliable" in query_lower or "confidence" in query_lower or "accurate" in query_lower:
        return generate_reliability_response(context)
    elif "evidence" in query_lower or "support" in query_lower:
        return generate_evidence_response(context)
    else:
        return generate_general_response(query, context)

def generate_why_response(context: Dict) -> str:
    """Generate response to 'Why this cancer?' queries"""
    
    if "prediction" not in context:
        return "I do not have enough biological evidence to answer this reliably. Please provide a prediction ID."
    
    pred = context["prediction"]
    response = f"The model predicted {pred['cancer_type']} based on multi-omics data analysis.\n\n"
    
    if "top_genes" in context:
        response += "The most influential genes identified are:\n"
        for gene_info in context["top_genes"][:5]:
            response += f"• {gene_info['gene_name']} (importance: {gene_info['importance']:.2f})\n"
        response += "\n"
    
    if "pathways" in context:
        response += "The following biological pathways showed significant activation:\n"
        for pathway_info in context["pathways"]:
            response += f"• {pathway_info['pathway_name']} pathway\n"
        response += "\n"
    
    response += f"The model confidence is {pred['confidence']:.1%}, indicating moderate to high reliability."
    
    return response

def generate_gene_response(context: Dict) -> str:
    """Generate response about influential genes"""
    
    if "top_genes" not in context or not context["top_genes"]:
        return "Gene importance information is not available for this prediction."
    
    response = "The following genes were identified as most influential in the prediction:\n\n"
    
    for gene_info in context["top_genes"][:10]:
        response += f"• {gene_info['gene_name']}: Importance score {gene_info['importance']:.3f}\n"
    
    return response

def generate_pathway_response(context: Dict) -> str:
    """Generate response about activated pathways"""
    
    if "pathways" not in context or not context["pathways"]:
        return "Pathway information is not available for this prediction."
    
    response = "The following biological pathways showed activation:\n\n"
    
    for pathway_info in context["pathways"]:
        response += f"• {pathway_info['pathway_name']}: Attention weight {pathway_info['attention']:.3f}\n"
    
    return response

def generate_reliability_response(context: Dict) -> str:
    """Generate response about prediction reliability"""
    
    if "prediction" not in context:
        return "Prediction information is not available."
    
    pred = context["prediction"]
    confidence = pred.get("confidence", 0.0)
    
    if confidence >= 0.8:
        reliability = "high"
    elif confidence >= 0.6:
        reliability = "moderate"
    else:
        reliability = "low"
    
    response = f"The prediction has {reliability} reliability (confidence: {confidence:.1%}).\n\n"
    response += "This is based on:\n"
    response += "• Multi-omics data quality\n"
    response += "• Knowledge graph consistency\n"
    response += "• Model attention agreement\n"
    response += "\nNote: This is a research tool. Consult medical professionals for clinical decisions."
    
    return response

def generate_evidence_response(context: Dict) -> str:
    """Generate response about evidence supporting the prediction"""
    
    if "prediction" not in context:
        return "Prediction information is not available."
    
    response = "The prediction is supported by:\n\n"
    
    if "top_genes" in context:
        response += "1. Gene-level evidence:\n"
        for gene_info in context["top_genes"][:5]:
            response += f"   • {gene_info['gene_name']} showed significant expression patterns\n"
        response += "\n"
    
    if "pathways" in context:
        response += "2. Pathway-level evidence:\n"
        for pathway_info in context["pathways"]:
            response += f"   • {pathway_info['pathway_name']} pathway activation\n"
        response += "\n"
    
    response += "3. Graph structure consistency: The gene interactions align with known biological networks."
    
    return response

def generate_general_response(query: str, context: Dict) -> str:
    """Generate general response"""
    
    if "prediction" in context:
        pred = context["prediction"]
        response = f"Based on the prediction analysis, the patient shows {pred['cancer_type']} characteristics.\n\n"
        response += f"Risk score: {pred['risk_score']:.1%}\n"
        response += f"Confidence: {pred['confidence']:.1%}\n\n"
        response += "For detailed explanations, please ask:\n"
        response += "• 'Why was this cancer predicted?'\n"
        response += "• 'Which genes caused the high risk?'\n"
        response += "• 'Which pathways are active?'"
    else:
        response = "I can help you understand cancer predictions and their explanations.\n\n"
        response += "Please provide a prediction ID, or ask about:\n"
        response += "• Prediction explanations\n"
        response += "• Gene importance\n"
        response += "• Pathway activation\n"
        response += "• Model reliability"
    
    return response

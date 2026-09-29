import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import AdminLayout from '../components/AdminLayout';
import axios from 'axios';

const API_URL = process.env.REACT_APP_API_URL || '';

function ExplanationView() {
  const { predictionId } = useParams();
  const navigate = useNavigate();
  const [explanations, setExplanations] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadExplanations();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [predictionId]);

  const loadExplanations = async () => {
    try {
      const token = localStorage.getItem('token');
      const response = await axios.get(
        `${API_URL}/api/explanation/prediction/${predictionId}`,
        { headers: { Authorization: `Bearer ${token}` } }
      );
      setExplanations(response.data);
    } catch (error) {
      console.error('Error loading explanations:', error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <AdminLayout>
        <div className="p-8 flex items-center justify-center min-h-screen">
          <div className="text-xl">Loading explanations...</div>
        </div>
      </AdminLayout>
    );
  }

  if (!explanations) {
    return (
      <AdminLayout>
        <div className="p-8 flex items-center justify-center min-h-screen">
          <div className="text-xl text-red-600">Failed to load explanations</div>
        </div>
      </AdminLayout>
    );
  }

  return (
    <AdminLayout>
      <div className="p-8">
        <div className="mb-6">
          <h2 className="text-3xl font-bold text-gray-900">Prediction Explanation</h2>
          <p className="mt-2 text-gray-600">Understand why this prediction was made</p>
        </div>
        <div className="space-y-6">
          {/* Gene Importance */}
          <div className="bg-white rounded-lg shadow-md p-6">
            <h2 className="text-xl font-bold mb-4">Top Influential Genes</h2>
            <div className="space-y-2">
              {explanations.gene_importance?.slice(0, 20).map((gene, idx) => {
                const pct = (gene.importance_score != null ? gene.importance_score : 0) * 100;
                return (
                  <div key={idx} className="flex items-center justify-between p-3 bg-gray-50 rounded">
                    <span className="font-medium">{gene.gene_name}</span>
                    <div className="flex items-center space-x-4">
                      <span className="text-sm text-gray-600">Importance: {pct.toFixed(1)}%</span>
                      <div className="w-48 bg-gray-200 rounded-full h-2">
                        <div
                          className="bg-indigo-600 h-2 rounded-full"
                          style={{ width: `${Math.min(100, pct)}%` }}
                        />
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Pathway Activation */}
          <div className="bg-white rounded-lg shadow-md p-6">
            <h2 className="text-xl font-bold mb-4">Activated Pathways</h2>
            <div className="space-y-2">
              {explanations.pathway_activation?.map((pathway, idx) => {
                const pct = (pathway.attention_weight != null ? pathway.attention_weight : 0) * 100;
                return (
                  <div key={idx} className="flex items-center justify-between p-3 bg-gray-50 rounded">
                    <span className="font-medium">{pathway.pathway_name}</span>
                    <div className="flex items-center space-x-4">
                      <span className="text-sm text-gray-600">Attention: {pct.toFixed(1)}%</span>
                      <div className="w-48 bg-gray-200 rounded-full h-2">
                        <div
                          className="bg-green-600 h-2 rounded-full"
                          style={{ width: `${Math.min(100, pct)}%` }}
                        />
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Action Buttons */}
          <div className="flex space-x-4">
            <button
              onClick={() => navigate(`/chatbot?predictionId=${predictionId}`)}
              className="px-6 py-3 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700"
            >
              Ask AI Assistant
            </button>
            <button
              onClick={() => navigate('/predictions')}
              className="px-6 py-3 bg-gray-200 text-gray-700 rounded-lg hover:bg-gray-300"
            >
              Back to Predictions
            </button>
          </div>
        </div>
      </div>
    </AdminLayout>
  );
}

export default ExplanationView;

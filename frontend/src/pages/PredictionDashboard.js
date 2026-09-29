import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import AdminLayout from '../components/AdminLayout';
import axios from 'axios';

const API_URL = process.env.REACT_APP_API_URL || '';

function PredictionDashboard() {
  const navigate = useNavigate();
  const [predictions, setPredictions] = useState([]);
  const [patients, setPatients] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedPatient, setSelectedPatient] = useState(null);
  const [predicting, setPredicting] = useState(false);
  const [lastRiskScores, setLastRiskScores] = useState(null);

  useEffect(() => {
    loadPredictions();
    loadPatients();
  }, []);

  const loadPredictions = async () => {
    try {
      const token = localStorage.getItem('token');
      const response = await axios.get(`${API_URL}/api/prediction/predictions`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setPredictions(response.data);
    } catch (error) {
      console.error('Error loading predictions:', error);
    } finally {
      setLoading(false);
    }
  };

  const loadPatients = async () => {
    try {
      const token = localStorage.getItem('token');
      // Only patients with omics data can be used for prediction (avoids "No omics data found")
      const response = await axios.get(`${API_URL}/api/patients/?with_omics_only=true`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setPatients(response.data);
    } catch (error) {
      console.error('Error loading patients:', error);
    }
  };

  const handlePredict = async (patientId) => {
    if (!patientId) {
      alert('Please select a patient');
      return;
    }
    
    setPredicting(true);
    try {
      const token = localStorage.getItem('token');
      const response = await axios.post(
        `${API_URL}/api/prediction/predict`,
        { patient_id: patientId },
        { headers: { Authorization: `Bearer ${token}` } }
      );
      
      setPredictions([response.data, ...predictions]);
      setSelectedPatient(null);
      setLastRiskScores(response.data.risk_scores || null);
      const confPct = (response.data.confidence * 100).toFixed(1);
      const riskSummary = response.data.risk_scores
        ? Object.entries(response.data.risk_scores)
            .sort((a, b) => b[1] - a[1])
            .slice(0, 5)
            .map(([k, v]) => `${k} ${(v * 100).toFixed(0)}%`)
            .join(', ')
        : '';
      alert(`Prediction created!\nCancer Type: ${response.data.cancer_type}\nConfidence: ${confPct}%\n${riskSummary ? `All probabilities: ${riskSummary}` : ''}`);
      navigate(`/explain/${response.data.prediction_id}`);
    } catch (error) {
      const data = error.response?.data;
      const detail = typeof data?.detail === 'string' ? data.detail : 'Prediction failed';
      if (error.response?.status === 503 && (data?.code === 'NO_MODEL' || data?.action === 'train_model')) {
        const goTrain = window.confirm(detail + '\n\nOpen Model Training page now?');
        if (goTrain) navigate('/training');
      } else {
        alert(detail);
      }
    } finally {
      setPredicting(false);
    }
  };

  if (loading) {
    return (
      <AdminLayout>
        <div className="p-8 flex items-center justify-center min-h-screen">
          <div className="text-xl">Loading...</div>
        </div>
      </AdminLayout>
    );
  }

  return (
    <AdminLayout>
      <div className="p-8">
        <div className="mb-6">
          <h2 className="text-3xl font-bold text-gray-900">Predictions</h2>
          <p className="mt-2 text-gray-600">View and manage all cancer predictions</p>
        </div>

        {/* Create New Prediction Section */}
        <div className="bg-white rounded-lg shadow-md p-6 mb-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Create New Prediction</h3>
          <div className="flex gap-4 items-end">
            <div className="flex-1">
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Select Patient (with omics data) {patients.length > 0 && `(${patients.length} available)`}
              </label>
              <select
                value={selectedPatient || ''}
                onChange={(e) => setSelectedPatient(e.target.value ? parseInt(e.target.value) : null)}
                className="w-full px-4 py-2 border border-gray-300 rounded-md focus:ring-indigo-500 focus:border-indigo-500"
              >
                <option value="">-- Select a patient --</option>
                {patients.map((patient) => (
                  <option key={patient.patient_id} value={patient.patient_id}>
                    Patient #{patient.patient_id} {patient.cancer_type ? `(${patient.cancer_type})` : ''}
                  </option>
                ))}
              </select>
              {patients.length === 0 && !loading && (
                <p className="mt-2 text-sm text-amber-600">
                  No patients with omics data. Upload <strong>cancer_multiomics_data.csv</strong> (with patient_id, gene_name, value, omics_type, cancer_type) from Upload Data, then patients here will appear.
                </p>
              )}
            </div>
            <button
              onClick={() => handlePredict(selectedPatient)}
              disabled={!selectedPatient || predicting}
              className="px-6 py-2 bg-indigo-600 text-white rounded-md hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {predicting ? 'Generating...' : 'Generate Prediction'}
            </button>
          </div>
          {patients.length === 0 && (
            <p className="mt-2 text-sm text-gray-500">No patients available. Please upload patient data first.</p>
          )}
          {lastRiskScores && Object.keys(lastRiskScores).length > 0 && (
            <div className="mt-4 p-4 bg-gray-50 rounded-lg border border-gray-200">
              <h4 className="text-sm font-semibold text-gray-700 mb-2">All class probabilities (last prediction)</h4>
              <div className="flex flex-wrap gap-3">
                {Object.entries(lastRiskScores)
                  .sort((a, b) => b[1] - a[1])
                  .map(([cancerType, p]) => (
                    <span key={cancerType} className="inline-flex items-center px-3 py-1 rounded-full text-sm bg-white border border-gray-200">
                      <span className="font-medium text-gray-800">{cancerType}</span>
                      <span className="ml-2 text-gray-600">{(p * 100).toFixed(1)}%</span>
                    </span>
                  ))}
              </div>
            </div>
          )}
        </div>

        {/* Predictions List */}
        <div className="bg-white rounded-lg shadow-md overflow-hidden">

          {predictions.length === 0 ? (
            <div className="p-8 text-center text-gray-500">
              No predictions yet. Upload patient data and create predictions.
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Patient ID</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Cancer Type</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Risk Score</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Confidence</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Date</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Actions</th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {predictions.map((pred) => (
                    <tr key={pred.prediction_id} className="hover:bg-gray-50">
                      <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                        {pred.patient_id}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                        {pred.cancer_type}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                        {(pred.risk_score * 100).toFixed(1)}%
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                        {(pred.confidence * 100).toFixed(1)}%
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                        {new Date(pred.created_at).toLocaleDateString()}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm">
                        <button
                          onClick={() => navigate(`/explain/${pred.prediction_id}`)}
                          className="text-indigo-600 hover:text-indigo-900 mr-4"
                        >
                          Explain
                        </button>
                        <button
                          onClick={() => navigate(`/chatbot?predictionId=${pred.prediction_id}`)}
                          className="text-green-600 hover:text-green-900"
                        >
                          Chat
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </AdminLayout>
  );
}

export default PredictionDashboard;

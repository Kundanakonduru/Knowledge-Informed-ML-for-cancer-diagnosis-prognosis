import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import AdminLayout from '../components/AdminLayout';
import axios from 'axios';

const API_URL = process.env.REACT_APP_API_URL || '';

function Dashboard() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [stats, setStats] = useState({
    patients: 0,
    predictions: 0,
    activeModel: null,
    loading: true
  });

  useEffect(() => {
    loadStats();
  }, []);

  const loadStats = async () => {
    try {
      const token = localStorage.getItem('token');
      const headers = { Authorization: `Bearer ${token}` };

      // Get patients count
      const patientsRes = await axios.get(`${API_URL}/api/patients/`, { headers });
      
      // Get predictions count
      try {
        const predictionsRes = await axios.get(`${API_URL}/api/prediction/predictions`, { headers });
        setStats(prev => ({ ...prev, predictions: predictionsRes.data.length || 0 }));
      } catch (e) {
        setStats(prev => ({ ...prev, predictions: 0 }));
      }
      
      // Get active model
      try {
        const modelRes = await axios.get(`${API_URL}/api/training/models/active`, { headers });
        if (modelRes.data) {
          setStats(prev => ({ ...prev, activeModel: modelRes.data }));
        }
      } catch (e) {
        // No active model yet - endpoint returns null, not error
        setStats(prev => ({ ...prev, activeModel: null }));
      }

      setStats(prev => ({
        ...prev,
        patients: patientsRes.data.length || 0,
        loading: false
      }));
    } catch (error) {
      console.error('Error loading stats:', error);
      setStats(prev => ({ ...prev, loading: false }));
    }
  };

  return (
    <AdminLayout>
      <div className="p-8">
        {/* Header */}
        <div className="mb-8">
          <h2 className="text-3xl font-bold text-gray-900">Dashboard</h2>
          <p className="mt-2 text-gray-600">
            Welcome back, {user?.name}! Here's an overview of your cancer diagnosis platform.
          </p>
        </div>

        {/* Stats Cards */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
          <div className="bg-white rounded-lg shadow-md p-6 border-l-4 border-indigo-500">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-sm font-medium text-gray-600 mb-1">Total Patients</h3>
                <p className="text-3xl font-bold text-indigo-600">{stats.patients}</p>
              </div>
              <div className="text-4xl">👥</div>
            </div>
          </div>
          
          <div className="bg-white rounded-lg shadow-md p-6 border-l-4 border-green-500">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-sm font-medium text-gray-600 mb-1">Predictions</h3>
                <p className="text-3xl font-bold text-green-600">{stats.predictions}</p>
              </div>
              <div className="text-4xl">🔮</div>
            </div>
          </div>
          
          <div className="bg-white rounded-lg shadow-md p-6 border-l-4 border-blue-500">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-sm font-medium text-gray-600 mb-1">Model Accuracy</h3>
                <p className="text-3xl font-bold text-blue-600">
                  {stats.activeModel && stats.activeModel.accuracy 
                    ? `${(stats.activeModel.accuracy * 100).toFixed(1)}%` 
                    : 'N/A'}
                </p>
                {stats.activeModel && (
                  <p className="text-xs text-gray-500 mt-1">v{stats.activeModel.version}</p>
                )}
              </div>
              <div className="text-4xl">🤖</div>
            </div>
          </div>
        </div>

        {/* Quick Actions Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          <button
            onClick={() => navigate('/upload')}
            className="bg-white rounded-lg shadow-md p-6 text-left hover:shadow-lg transition-all border border-gray-200 hover:border-indigo-500"
          >
            <div className="text-3xl mb-3">📤</div>
            <h3 className="text-lg font-semibold text-gray-900 mb-2">Upload Patient Data</h3>
            <p className="text-sm text-gray-600">Upload CSV files or enter data manually</p>
          </button>

          <button
            onClick={() => navigate('/predictions')}
            className="bg-white rounded-lg shadow-md p-6 text-left hover:shadow-lg transition-all border border-gray-200 hover:border-green-500"
          >
            <div className="text-3xl mb-3">🔮</div>
            <h3 className="text-lg font-semibold text-gray-900 mb-2">View Predictions</h3>
            <p className="text-sm text-gray-600">See all cancer predictions and results</p>
          </button>

          <button
            onClick={() => navigate('/chatbot')}
            className="bg-white rounded-lg shadow-md p-6 text-left hover:shadow-lg transition-all border border-gray-200 hover:border-purple-500"
          >
            <div className="text-3xl mb-3">💬</div>
            <h3 className="text-lg font-semibold text-gray-900 mb-2">Clinical Assistant</h3>
            <p className="text-sm text-gray-600">Ask questions about predictions</p>
          </button>

          {user?.role === 'admin' && (
            <button
              onClick={() => navigate('/training')}
              className="bg-white rounded-lg shadow-md p-6 text-left hover:shadow-lg transition-all border border-gray-200 hover:border-blue-500"
            >
              <div className="text-3xl mb-3">🤖</div>
              <h3 className="text-lg font-semibold text-gray-900 mb-2">Model Training</h3>
              <p className="text-sm text-gray-600">Manage model training and versions</p>
            </button>
          )}
        </div>

        {/* Recent Activity Section */}
        {user?.role === 'admin' && (
          <div className="mt-8 bg-white rounded-lg shadow-md p-6">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">Admin Quick Actions</h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <button
                onClick={() => navigate('/training')}
                className="px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition"
              >
                Train New Model
              </button>
              <button
                onClick={() => navigate('/upload')}
                className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition"
              >
                Import Data
              </button>
            </div>
          </div>
        )}
      </div>
    </AdminLayout>
  );
}

export default Dashboard;

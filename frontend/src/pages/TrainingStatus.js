import React, { useState, useEffect, useRef } from 'react';
import { useAuth } from '../context/AuthContext';
import AdminLayout from '../components/AdminLayout';
import axios from 'axios';

const API_URL = process.env.REACT_APP_API_URL || '';

function TrainingStatus() {
  const { user } = useAuth();
  const [models, setModels] = useState([]);
  const [jobs, setJobs] = useState([]);
  const [loading, setLoading] = useState(true);
  const pollRef = useRef(null);

  const loadModels = async () => {
    try {
      const token = localStorage.getItem('token');
      const response = await axios.get(`${API_URL}/api/training/models`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setModels(response.data);
    } catch (error) {
      console.error('Error loading models:', error);
    } finally {
      setLoading(false);
    }
  };

  const loadJobs = async () => {
    try {
      const token = localStorage.getItem('token');
      const response = await axios.get(`${API_URL}/api/training/jobs`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setJobs(response.data || []);
    } catch (error) {
      console.error('Error loading jobs:', error);
    }
  };

  useEffect(() => {
    loadModels();
    loadJobs();
  }, []);

  // Poll jobs when any job is queued or running
  const hasActiveJob = jobs.some(j => j.status === 'queued' || j.status === 'running');
  useEffect(() => {
    if (!hasActiveJob) return;
    pollRef.current = setInterval(() => {
      loadJobs();
      loadModels();
    }, 3000);
    return () => { if (pollRef.current) clearInterval(pollRef.current); };
  }, [hasActiveJob]);

  const triggerTraining = async () => {
    try {
      const token = localStorage.getItem('token');
      await axios.post(`${API_URL}/api/training/trigger`, {}, {
        headers: { Authorization: `Bearer ${token}` }
      });
      alert('Training job queued successfully!');
      loadModels();
      loadJobs();
    } catch (error) {
      alert(error.response?.data?.detail || 'Failed to trigger training');
    }
  };

  if (user?.role !== 'admin') {
    return (
      <AdminLayout>
        <div className="p-8 flex items-center justify-center min-h-screen">
          <div className="text-xl text-red-600">Access denied. Admin only.</div>
        </div>
      </AdminLayout>
    );
  }

  return (
    <AdminLayout>
      <div className="p-8">
        <div className="mb-6">
          <h2 className="text-3xl font-bold text-gray-900">Model Training</h2>
          <p className="mt-2 text-gray-600">Manage model training and versions</p>
        </div>
        <div className="mb-6">
          <button
            onClick={triggerTraining}
            className="px-6 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700"
          >
            Trigger Training
          </button>
        </div>

        {/* Recent training jobs (upload → train pipeline) */}
        <div className="mb-8">
          <h3 className="text-lg font-semibold text-gray-900 mb-3">Recent training jobs</h3>
          <div className="bg-white rounded-lg shadow overflow-hidden">
            {jobs.length === 0 ? (
              <div className="p-4 text-center text-gray-500 text-sm">No training jobs yet. Upload a CSV or click Trigger Training.</div>
            ) : (
              <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Job ID</th>
                    <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Status</th>
                    <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Trigger</th>
                    <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Accuracy</th>
                    <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Created</th>
                    <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Completed</th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {jobs.map((job) => (
                    <tr key={job.job_id} className="hover:bg-gray-50">
                      <td className="px-4 py-2 text-sm font-medium text-gray-900">{job.job_id}</td>
                      <td className="px-4 py-2">
                        <span className={`px-2 py-0.5 text-xs rounded-full ${
                          job.status === 'completed' ? 'bg-green-100 text-green-800' :
                          job.status === 'running' || job.status === 'queued' ? 'bg-yellow-100 text-yellow-800' :
                          job.status === 'failed' ? 'bg-red-100 text-red-800' : 'bg-gray-100 text-gray-800'
                        }`}>
                          {job.status}
                        </span>
                      </td>
                      <td className="px-4 py-2 text-sm text-gray-600">{job.trigger_type || '—'}</td>
                      <td className="px-4 py-2 text-sm text-gray-600">
                        {job.accuracy_after != null ? `${(job.accuracy_after * 100).toFixed(2)}%` : '—'}
                      </td>
                      <td className="px-4 py-2 text-sm text-gray-500">{job.created_at ? new Date(job.created_at).toLocaleString() : '—'}</td>
                      <td className="px-4 py-2 text-sm text-gray-500">{job.completed_at ? new Date(job.completed_at).toLocaleString() : '—'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
            {jobs.some(j => j.status === 'queued' || j.status === 'running') && (
              <div className="p-2 text-center text-sm text-amber-600">Refreshing job status every 3s…</div>
            )}
          </div>
        </div>

        <div className="bg-white rounded-lg shadow overflow-hidden">
          {loading ? (
            <div className="p-8 text-center text-gray-500">
              <p>Loading models...</p>
            </div>
          ) : models.length === 0 ? (
            <div className="p-8 text-center text-gray-500">
              <p className="text-lg mb-2">No trained models yet.</p>
              <p className="text-sm">Click "Trigger Training" to train your first model.</p>
            </div>
          ) : (
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Version</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Type</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Accuracy</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Samples</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Status</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Trained On</th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {models.map((model) => (
                  <tr key={model.model_id} className="hover:bg-gray-50">
                    <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">{model.version}</td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">{model.model_type}</td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                      {model.accuracy ? `${(model.accuracy * 100).toFixed(2)}%` : 'N/A'}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">{model.training_samples || 'N/A'}</td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span className={`px-2 py-1 text-xs rounded-full ${
                        model.status === 'active' ? 'bg-green-100 text-green-800' :
                        model.status === 'training' ? 'bg-yellow-100 text-yellow-800' :
                        'bg-gray-100 text-gray-800'
                      }`}>
                        {model.status}
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {model.trained_on ? new Date(model.trained_on).toLocaleDateString() : 'N/A'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </AdminLayout>
  );
}

export default TrainingStatus;

import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import AdminLayout from '../components/AdminLayout';
import axios from 'axios';

const API_URL = process.env.REACT_APP_API_URL || '';

const CANCER_TYPES = ['BRCA', 'LUAD', 'COAD', 'PRAD', 'KIRC', 'THCA'];
const OMICS_TYPES = ['mRNA', 'miRNA', 'methylation'];

const initialOmicsRow = () => ({ gene_name: '', value: '', omics_type: 'mRNA' });

function PatientUpload() {
  const navigate = useNavigate();
  const [files, setFiles] = useState([]);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState('');
  const [uploadMode, setUploadMode] = useState('csv');
  const [uploadProgress, setUploadProgress] = useState({});
  const [uploadTriggeredJobId, setUploadTriggeredJobId] = useState(null);

  // Manual entry state
  const [manualForm, setManualForm] = useState({
    age: '',
    gender: 'M',
    cancer_type: '',
    clinical_info: '',
    omics_data: [initialOmicsRow()]
  });

  const handleFileChange = (e) => {
    const selectedFiles = Array.from(e.target.files);
    setFiles(selectedFiles);
    setMessage('');
  };

  const handleCSVUpload = async (e) => {
    e.preventDefault();
    if (files.length === 0) {
      setMessage('Please select at least one CSV file');
      return;
    }

    setLoading(true);
    setMessage('');
    setUploadProgress({});

    try {
      const token = localStorage.getItem('token');
      let totalPatients = 0;
      let totalOmicsRecords = 0;
      let successCount = 0;
      let errorCount = 0;
      let lastJobId = null;
      const errors = [];

      // Upload files one by one
      for (let i = 0; i < files.length; i++) {
        const file = files[i];
        setUploadProgress({ current: i + 1, total: files.length, fileName: file.name });

        try {
          const formData = new FormData();
          formData.append('file', file);

          const response = await axios.post(
            `${API_URL}/api/upload/csv`,
            formData,
            {
              headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'multipart/form-data'
              }
            }
          );

          totalPatients += response.data.patients_added || 0;
          totalOmicsRecords += response.data.omics_records_added || 0;
          if (response.data.auto_training_triggered && response.data.job_id) {
            lastJobId = response.data.job_id;
          }
          successCount++;
        } catch (error) {
          errorCount++;
          errors.push(`${file.name}: ${error.response?.data?.detail || 'Upload failed'}`);
        }
      }

      // Show summary
      let summaryMessage = `Upload complete! ${successCount} file(s) uploaded successfully.`;
      if (totalPatients > 0) {
        summaryMessage += ` ${totalPatients} patients added. ${totalOmicsRecords} omics records added.`;
      }
      if (lastJobId != null) {
        summaryMessage += ` Model training started (Job #${lastJobId}). Check Training page for status.`;
      }
      if (errorCount > 0) {
        summaryMessage += ` ${errorCount} file(s) failed.`;
        setMessage(summaryMessage + '\n' + errors.join('\n'));
      } else {
        setMessage(summaryMessage);
      }

      setFiles([]);
      setUploadProgress({});
      if (lastJobId != null) setUploadTriggeredJobId(lastJobId);
      
      if (successCount > 0) {
        setTimeout(() => navigate('/predictions'), 3000);
      }
    } catch (error) {
      setMessage(error.response?.data?.detail || 'Upload failed');
    } finally {
      setLoading(false);
      setUploadProgress({});
    }
  };

  const handleManualFieldChange = (field, value) => {
    setManualForm(prev => ({ ...prev, [field]: value }));
    setMessage('');
  };

  const handleOmicsRowChange = (index, field, value) => {
    setManualForm(prev => ({
      ...prev,
      omics_data: prev.omics_data.map((row, i) =>
        i === index ? { ...row, [field]: value } : row
      )
    }));
    setMessage('');
  };

  const addOmicsRow = () => {
    setManualForm(prev => ({
      ...prev,
      omics_data: [...prev.omics_data, initialOmicsRow()]
    }));
  };

  const removeOmicsRow = (index) => {
    if (manualForm.omics_data.length <= 1) return;
    setManualForm(prev => ({
      ...prev,
      omics_data: prev.omics_data.filter((_, i) => i !== index)
    }));
  };

  const handleManualSubmit = async (e) => {
    e.preventDefault();
    const ageNum = manualForm.age === '' ? null : parseInt(manualForm.age, 10);
    const cancerType = manualForm.cancer_type.trim() || null;
    const clinicalInfo = manualForm.clinical_info.trim() || null;

    const validOmics = manualForm.omics_data.filter(
      row => row.gene_name.trim() !== '' && row.value !== '' && !isNaN(parseFloat(row.value))
    );
    if (validOmics.length === 0) {
      setMessage('Add at least one omics row with gene name and value.');
      return;
    }

    const payload = {
      age: ageNum,
      gender: manualForm.gender,
      cancer_type: cancerType,
      clinical_info: clinicalInfo,
      omics_data: validOmics.map(row => ({
        gene_name: row.gene_name.trim(),
        value: parseFloat(row.value),
        omics_type: row.omics_type
      }))
    };

    setLoading(true);
    setMessage('');
    try {
      const token = localStorage.getItem('token');
      const response = await axios.post(
        `${API_URL}/api/upload/manual`,
        payload,
        {
          headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json'
          }
        }
      );
      setMessage(`Success! Patient created (ID: ${response.data.patient_id}). You can add more or go to Predictions.`);
      setManualForm({
        age: '',
        gender: 'M',
        cancer_type: '',
        clinical_info: '',
        omics_data: [initialOmicsRow()]
      });
      setTimeout(() => navigate('/predictions'), 2000);
    } catch (error) {
      setMessage(error.response?.data?.detail || 'Manual upload failed.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <AdminLayout>
      <div className="p-8">
        <div className="mb-6">
          <h2 className="text-3xl font-bold text-gray-900">Upload Patient Data</h2>
          <p className="mt-2 text-gray-600">Upload CSV files or enter data manually</p>
        </div>

        <div className="bg-white rounded-lg shadow-md p-6">

          {/* Tabs */}
          <div className="flex space-x-4 mb-6 border-b">
            <button
              onClick={() => setUploadMode('csv')}
              className={`px-4 py-2 font-medium ${uploadMode === 'csv' ? 'border-b-2 border-indigo-600 text-indigo-600' : 'text-gray-600'}`}
            >
              CSV Upload
            </button>
            <button
              onClick={() => setUploadMode('manual')}
              className={`px-4 py-2 font-medium ${uploadMode === 'manual' ? 'border-b-2 border-indigo-600 text-indigo-600' : 'text-gray-600'}`}
            >
              Manual Entry
            </button>
          </div>

          {uploadMode === 'csv' ? (
            <form onSubmit={handleCSVUpload} className="space-y-6">
              <div className="rounded-lg bg-gray-50 border border-gray-200 p-3 text-sm text-gray-600">
                <strong>CSV format (required):</strong> <code>patient_id</code>, <code>gene_name</code>, <code>value</code>. Optional: <code>omics_type</code> (mRNA, miRNA, methylation), <code>cancer_type</code>, <code>age</code>, <code>gender</code>. One row per gene per patient. Multi-omics (one file with mRNA + methylation + miRNA) is supported. After upload, go to <strong>Predictions</strong> to select a patient and generate prediction; training runs in background (check <strong>Model Training</strong>).
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Select CSV File(s) - You can select multiple files
                </label>
                <input
                  type="file"
                  accept=".csv"
                  multiple
                  onChange={handleFileChange}
                  className="block w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-md file:border-0 file:text-sm file:font-semibold file:bg-indigo-50 file:text-indigo-700 hover:file:bg-indigo-100"
                />
                <p className="mt-2 text-sm text-gray-500">
                  CSV should contain: patient_id, gene_name, value, omics_type (mRNA, miRNA, methylation)
                </p>
                {files.length > 0 && (
                  <div className="mt-3 p-3 bg-gray-50 rounded-md">
                    <p className="text-sm font-medium text-gray-700 mb-2">
                      Selected files ({files.length}):
                    </p>
                    <ul className="list-disc list-inside text-sm text-gray-600 space-y-1">
                      {files.map((file, idx) => (
                        <li key={idx}>{file.name} ({(file.size / 1024).toFixed(1)} KB)</li>
                      ))}
                    </ul>
                  </div>
                )}
                {uploadProgress.current && (
                  <div className="mt-3 p-3 bg-blue-50 rounded-md">
                    <p className="text-sm text-blue-700">
                      Uploading {uploadProgress.current} of {uploadProgress.total}: {uploadProgress.fileName}
                    </p>
                  </div>
                )}
              </div>

              {message && (
                <div className={`p-4 rounded-md whitespace-pre-line ${message.includes('Success') || message.includes('complete') ? 'bg-green-50 text-green-800' : 'bg-red-50 text-red-800'}`}>
                  {message}
                  {uploadTriggeredJobId != null && (
                    <div className="mt-3">
                      <button
                        type="button"
                        onClick={() => { setUploadTriggeredJobId(null); navigate('/training'); }}
                        className="px-3 py-1.5 bg-indigo-600 text-white text-sm rounded hover:bg-indigo-700"
                      >
                        View training status
                      </button>
                    </div>
                  )}
                </div>
              )}

              <button
                type="submit"
                disabled={loading || files.length === 0}
                className="w-full px-4 py-2 bg-indigo-600 text-white rounded-md hover:bg-indigo-700 disabled:opacity-50"
              >
                {loading ? 'Uploading...' : 'Upload CSV'}
              </button>
            </form>
          ) : (
            <form onSubmit={handleManualSubmit} className="space-y-6">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Age</label>
                  <input
                    type="number"
                    min="1"
                    max="120"
                    value={manualForm.age}
                    onChange={(e) => handleManualFieldChange('age', e.target.value)}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-indigo-500 focus:border-indigo-500"
                    placeholder="e.g. 55"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Gender</label>
                  <select
                    value={manualForm.gender}
                    onChange={(e) => handleManualFieldChange('gender', e.target.value)}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-indigo-500 focus:border-indigo-500"
                  >
                    <option value="M">Male</option>
                    <option value="F">Female</option>
                    <option value="Other">Other</option>
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Cancer Type</label>
                  <select
                    value={manualForm.cancer_type}
                    onChange={(e) => handleManualFieldChange('cancer_type', e.target.value)}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-indigo-500 focus:border-indigo-500"
                  >
                    <option value="">Select type</option>
                    {CANCER_TYPES.map(t => (
                      <option key={t} value={t}>{t}</option>
                    ))}
                  </select>
                </div>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Clinical Info (optional)</label>
                <textarea
                  value={manualForm.clinical_info}
                  onChange={(e) => handleManualFieldChange('clinical_info', e.target.value)}
                  rows={2}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-indigo-500 focus:border-indigo-500"
                  placeholder="Notes or clinical details"
                />
              </div>

              <div>
                <div className="flex items-center justify-between mb-2">
                  <label className="block text-sm font-medium text-gray-700">Omics Data (gene, value, type)</label>
                  <button
                    type="button"
                    onClick={addOmicsRow}
                    className="text-sm text-indigo-600 hover:text-indigo-800"
                  >
                    + Add row
                  </button>
                </div>
                <div className="space-y-2 max-h-48 overflow-y-auto border border-gray-200 rounded-md p-2 bg-gray-50">
                  {manualForm.omics_data.map((row, index) => (
                    <div key={index} className="flex flex-wrap gap-2 items-center">
                      <input
                        type="text"
                        value={row.gene_name}
                        onChange={(e) => handleOmicsRowChange(index, 'gene_name', e.target.value)}
                        placeholder="Gene name"
                        className="flex-1 min-w-[100px] px-2 py-1.5 text-sm border border-gray-300 rounded"
                      />
                      <input
                        type="number"
                        step="any"
                        value={row.value}
                        onChange={(e) => handleOmicsRowChange(index, 'value', e.target.value)}
                        placeholder="Value"
                        className="w-24 px-2 py-1.5 text-sm border border-gray-300 rounded"
                      />
                      <select
                        value={row.omics_type}
                        onChange={(e) => handleOmicsRowChange(index, 'omics_type', e.target.value)}
                        className="w-28 px-2 py-1.5 text-sm border border-gray-300 rounded"
                      >
                        {OMICS_TYPES.map(t => (
                          <option key={t} value={t}>{t}</option>
                        ))}
                      </select>
                      <button
                        type="button"
                        onClick={() => removeOmicsRow(index)}
                        disabled={manualForm.omics_data.length <= 1}
                        className="text-red-600 hover:text-red-800 disabled:opacity-40 text-sm"
                      >
                        Remove
                      </button>
                    </div>
                  ))}
                </div>
                <p className="mt-1 text-xs text-gray-500">At least one row with gene name and value is required.</p>
              </div>

              {message && (
                <div className={`p-4 rounded-md whitespace-pre-line ${message.includes('Success') ? 'bg-green-50 text-green-800' : 'bg-red-50 text-red-800'}`}>
                  {message}
                </div>
              )}

              <button
                type="submit"
                disabled={loading}
                className="w-full px-4 py-2 bg-indigo-600 text-white rounded-md hover:bg-indigo-700 disabled:opacity-50"
              >
                {loading ? 'Saving...' : 'Save Patient & Omics Data'}
              </button>
            </form>
          )}

          {/* Info Box */}
          <div className="mt-6 p-4 bg-blue-50 rounded-md">
            <h3 className="font-semibold text-blue-900 mb-2">CSV Format:</h3>
            <pre className="text-sm text-blue-800">
{`patient_id,gene_name,value,omics_type,cancer_type
BRCA_P001,TP53,7885.4,mRNA,BRCA
BRCA_P001,BRCA1,652.7,mRNA,BRCA
...`}
            </pre>
            <p className="text-sm text-blue-700 mt-2">
              You can use the pre-generated data files in the <code>data/</code> directory.
            </p>
          </div>
        </div>
      </div>
    </AdminLayout>
  );
}

export default PatientUpload;

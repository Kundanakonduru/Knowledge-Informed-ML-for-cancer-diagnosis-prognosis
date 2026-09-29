import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider, useAuth } from './context/AuthContext';
import Login from './pages/Login';
import Register from './pages/Register';
import Dashboard from './pages/Dashboard';
import PatientUpload from './pages/PatientUpload';
import PredictionDashboard from './pages/PredictionDashboard';
import ExplanationView from './pages/ExplanationView';
import ChatbotInterface from './pages/ChatbotInterface';
import TrainingStatus from './pages/TrainingStatus';
import './index.css';

function PrivateRoute({ children }) {
  const { user, loading } = useAuth();
  
  if (loading) {
    return <div className="flex items-center justify-center min-h-screen">
      <div className="text-xl">Loading...</div>
    </div>;
  }
  
  return user ? children : <Navigate to="/login" />;
}

function App() {
  return (
    <AuthProvider>
      <Router>
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route path="/register" element={<Register />} />
          <Route path="/" element={
            <PrivateRoute>
              <Dashboard />
            </PrivateRoute>
          } />
          <Route path="/upload" element={
            <PrivateRoute>
              <PatientUpload />
            </PrivateRoute>
          } />
          <Route path="/predictions" element={
            <PrivateRoute>
              <PredictionDashboard />
            </PrivateRoute>
          } />
          <Route path="/explain/:predictionId" element={
            <PrivateRoute>
              <ExplanationView />
            </PrivateRoute>
          } />
          <Route path="/chatbot" element={
            <PrivateRoute>
              <ChatbotInterface />
            </PrivateRoute>
          } />
          <Route path="/training" element={
            <PrivateRoute>
              <TrainingStatus />
            </PrivateRoute>
          } />
        </Routes>
      </Router>
    </AuthProvider>
  );
}

export default App;

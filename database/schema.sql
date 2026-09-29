-- Knowledge-Informed ML for Cancer Diagnosis & Prognosis
-- Database Schema (MySQL)

CREATE DATABASE IF NOT EXISTS cancer_diagnosis_db;
USE cancer_diagnosis_db;

-- 1. Users Table (Multi-role: Admin, Doctor, Researcher)
CREATE TABLE IF NOT EXISTS users (
    user_id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role ENUM('admin', 'doctor', 'researcher') NOT NULL DEFAULT 'researcher',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_email (email),
    INDEX idx_role (role)
);

-- 2. Patients Table
CREATE TABLE IF NOT EXISTS patients (
    patient_id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    age INT,
    gender ENUM('M', 'F', 'Other'),
    cancer_type VARCHAR(100),
    clinical_info TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
    INDEX idx_user (user_id),
    INDEX idx_cancer_type (cancer_type)
);

-- 3. Omics Data Table (Multi-omics: mRNA, miRNA, DNA methylation)
CREATE TABLE IF NOT EXISTS omics_data (
    omics_id INT AUTO_INCREMENT PRIMARY KEY,
    patient_id INT NOT NULL,
    gene_name VARCHAR(255) NOT NULL,
    value FLOAT NOT NULL,
    omics_type ENUM('mRNA', 'miRNA', 'methylation') NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (patient_id) REFERENCES patients(patient_id) ON DELETE CASCADE,
    INDEX idx_patient (patient_id),
    INDEX idx_gene (gene_name),
    INDEX idx_omics_type (omics_type),
    INDEX idx_patient_gene (patient_id, gene_name, omics_type)
);

-- 4. Model Registry Table
CREATE TABLE IF NOT EXISTS model_registry (
    model_id INT AUTO_INCREMENT PRIMARY KEY,
    version VARCHAR(50) NOT NULL,
    model_type VARCHAR(100) NOT NULL DEFAULT 'GAT',
    accuracy FLOAT,
    training_samples INT,
    trained_on TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    model_path VARCHAR(500) NOT NULL,
    status ENUM('training', 'active', 'archived') DEFAULT 'active',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY unique_version (version),
    INDEX idx_status (status),
    INDEX idx_accuracy (accuracy)
);

-- 5. Predictions Table
CREATE TABLE IF NOT EXISTS predictions (
    prediction_id INT AUTO_INCREMENT PRIMARY KEY,
    patient_id INT NOT NULL,
    model_id INT NOT NULL,
    cancer_type VARCHAR(100) NOT NULL,
    risk_score FLOAT NOT NULL,
    confidence FLOAT,
    prognosis_score FLOAT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (patient_id) REFERENCES patients(patient_id) ON DELETE CASCADE,
    FOREIGN KEY (model_id) REFERENCES model_registry(model_id) ON DELETE CASCADE,
    INDEX idx_patient (patient_id),
    INDEX idx_cancer_type (cancer_type),
    INDEX idx_risk_score (risk_score)
);

-- 6. Explanations Table (Explainable AI)
CREATE TABLE IF NOT EXISTS explanations (
    explain_id INT AUTO_INCREMENT PRIMARY KEY,
    prediction_id INT NOT NULL,
    gene_name VARCHAR(255),
    importance_score FLOAT,
    pathway_name VARCHAR(255),
    attention_weight FLOAT,
    explanation_type ENUM('gene', 'pathway', 'attention') NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (prediction_id) REFERENCES predictions(prediction_id) ON DELETE CASCADE,
    INDEX idx_prediction (prediction_id),
    INDEX idx_gene (gene_name),
    INDEX idx_pathway (pathway_name)
);

-- 7. Training Jobs Table (Auto-training tracking)
CREATE TABLE IF NOT EXISTS training_jobs (
    job_id INT AUTO_INCREMENT PRIMARY KEY,
    trigger_type ENUM('new_data', 'manual', 'threshold') NOT NULL,
    status ENUM('queued', 'running', 'completed', 'failed') DEFAULT 'queued',
    model_id INT,
    new_samples_count INT,
    accuracy_before FLOAT,
    accuracy_after FLOAT,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    error_message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (model_id) REFERENCES model_registry(model_id) ON DELETE SET NULL,
    INDEX idx_status (status),
    INDEX idx_trigger (trigger_type)
);

-- 8. Chat History Table (Chatbot interactions)
CREATE TABLE IF NOT EXISTS chat_history (
    chat_id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    patient_id INT,
    prediction_id INT,
    query TEXT NOT NULL,
    response TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
    FOREIGN KEY (patient_id) REFERENCES patients(patient_id) ON DELETE SET NULL,
    FOREIGN KEY (prediction_id) REFERENCES predictions(prediction_id) ON DELETE SET NULL,
    INDEX idx_user (user_id),
    INDEX idx_patient (patient_id)
);

-- Insert default admin user (password: admin123)
-- Password hash for 'admin123' using bcrypt
INSERT INTO users (name, email, password_hash, role) VALUES
('Admin User', 'admin@cancerai.com', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5GyYFJY3NQ5qO', 'admin'),
('Dr. John Smith', 'doctor@cancerai.com', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5GyYFJY3NQ5qO', 'doctor'),
('Researcher Jane', 'researcher@cancerai.com', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5GyYFJY3NQ5qO', 'researcher')
ON DUPLICATE KEY UPDATE email=email;

-- Note: Default password for all test users is 'admin123'

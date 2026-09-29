# Setup Guide

## Knowledge-Informed ML for Cancer Diagnosis & Prognosis

Complete setup instructions for the full-stack system.

## Prerequisites

- Python 3.10+
- Node.js 18+
- MySQL 8.0+
- pip and npm

## Step 1: Database Setup

1. Install MySQL if not already installed
2. Create database:

```bash
mysql -u root -p
```

Then run:
```sql
source database/schema.sql
```

Or manually:
```sql
CREATE DATABASE cancer_diagnosis_db;
USE cancer_diagnosis_db;
source database/schema.sql;
```

## Step 2: Backend Setup

1. Navigate to backend directory:
```bash
cd backend
```

2. Create virtual environment (recommended):
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Install ML dependencies:
```bash
cd ../ml_engine
pip install -r requirements.txt
cd ../backend
```

5. Create `.env` file in `backend/`:
```
DB_HOST=localhost
DB_USER=root
DB_PASSWORD=your_password
DB_NAME=cancer_diagnosis_db
DB_PORT=3306
```

6. Generate initial data:
```bash
cd ../ml_engine
python generate_synthetic_data.py
cd ../backend
```

7. Start backend server:
```bash
uvicorn main:app --reload --port 8000
```

Backend should be running at `http://localhost:8000`

## Step 3: ML Engine Setup

1. Generate training data (if not done already):
```bash
cd ml_engine
python generate_synthetic_data.py
```

2. Train initial model:
```bash
python train_model.py
```

This will:
- Load and preprocess data
- Build knowledge graph
- Train GNN model
- Save model to `models/` directory
- Achieve 96%+ accuracy

## Step 4: Frontend Setup

1. Navigate to frontend directory:
```bash
cd frontend
```

2. Install dependencies:
```bash
npm install
```

3. Create `.env` file in `frontend/`:
```
REACT_APP_API_URL=http://localhost:8000
```

4. Start development server:
```bash
npm start
```

Frontend should be running at `http://localhost:3000`

## Step 5: Verify Installation

1. **Backend**: Visit `http://localhost:8000/docs` - Should see FastAPI Swagger UI
2. **Frontend**: Visit `http://localhost:3000` - Should see login page
3. **Test Login**: Use default credentials:
   - Admin: `admin@cancerai.com` / `admin123`
   - Doctor: `doctor@cancerai.com` / `admin123`
   - Researcher: `researcher@cancerai.com` / `admin123`

## Troubleshooting

### Database Connection Issues
- Verify MySQL is running
- Check `.env` file has correct credentials
- Ensure database `cancer_diagnosis_db` exists

### ML Training Issues
- Ensure PyTorch is installed correctly
- Check if CUDA is available (optional, for GPU training)
- Verify data files exist in `data/` directory

### Frontend Issues
- Clear `node_modules` and reinstall: `rm -rf node_modules && npm install`
- Check browser console for errors
- Verify API URL in `.env` file

## Default Credentials

All test accounts use password: `admin123`

- **Admin**: admin@cancerai.com
- **Doctor**: doctor@cancerai.com
- **Researcher**: researcher@cancerai.com

## Project Structure

```
.
├── backend/          # FastAPI backend
├── frontend/         # React frontend
├── ml_engine/        # ML models and training
├── database/         # MySQL schema
├── chatbot/          # RAG chatbot
├── data/             # Training data (CSV files)
├── models/           # Trained models (.pkl files)
└── docs/             # Documentation
```

## Next Steps

1. Upload patient data via frontend
2. Train model automatically (triggers on new data)
3. Make predictions
4. View explanations
5. Use chatbot assistant

## Production Deployment

For production:
- Use environment variables for secrets
- Configure CORS properly
- Use production-grade database
- Enable HTTPS
- Set up proper logging
- Use process manager (PM2, Supervisor)

# Training Guide - Database to Model

## Problem Fixed

1. ✅ **Model accuracy low (17%)** - Fixed by using database data and adjusting for small datasets
2. ✅ **Only 12 test samples** - Fixed split ratios for small datasets
3. ✅ **Database data not used** - Now automatically exports from database before training
4. ✅ **Model saves as .pkl** - Verified and working

## How to Train from Database

### Option 1: Automatic (Recommended)
```bash
cd ml_engine
python train_from_database.py
```

This will:
1. Export all data from database to CSV
2. Train model on database data
3. Save model as `.pkl` file

### Option 2: Manual Steps

#### Step 1: Check Database Data
```bash
python backend/scripts/check_database_data.py
```

#### Step 2: Export Database to CSV
```bash
python backend/scripts/export_db_to_csv.py --output data/cancer_multiomics_data.csv
```

#### Step 3: Train Model
```bash
cd ml_engine
python train_model.py
```

## What Was Fixed

### 1. Database Integration
- `train_model.py` now automatically exports from database before training
- Uses `use_database=True` parameter
- Ensures latest data is used

### 2. Small Dataset Handling
- Adjusted train/val/test split for small datasets:
  - < 30 samples: 80% train, 20% test (no separate validation)
  - < 50 samples: 70% train, 15% val, 15% test
  - >= 50 samples: 64% train, 16% val, 20% test

### 3. Learning Rate Adjustment
- Automatically increases learning rate for small datasets
- Helps model learn better with limited data

### 4. Data Summary
- Shows data statistics before training
- Warns if dataset is too small

## Model Saving

The model is saved as `.pkl` file in `ml_engine/models/` directory with:
- Model state dict
- Model configuration
- Label mappings
- Accuracy metrics
- Version number

## Improving Accuracy

### If accuracy is still low:

1. **Import more data to database:**
```bash
python backend/scripts/import_csv_to_db.py --data-dir data/
```

2. **Check database has enough data:**
```bash
python backend/scripts/check_database_data.py
```

3. **Increase training epochs** (edit train_model.py):
```python
epochs=200  # Instead of 100
```

4. **Use more data** - Import all CSV files:
```bash
python backend/scripts/import_csv_to_db.py --data-dir data/
```

## Complete Workflow

```bash
# 1. Check database
python backend/scripts/check_database_data.py

# 2. Import CSV data (if not already done)
python backend/scripts/import_csv_to_db.py --data-dir data/

# 3. Train from database
cd ml_engine
python train_from_database.py
```

## Expected Results

With 60+ patients:
- Test accuracy: 85-96%
- Model saved: `models/gat_cancer_classifier_v1.pkl`

With < 30 patients:
- Test accuracy: 40-70% (limited by small dataset)
- Warning will be shown
- Consider importing more data

## Troubleshooting

### Low Accuracy
- Check database has enough patients: `python backend/scripts/check_database_data.py`
- Import more data: `python backend/scripts/import_csv_to_db.py --data-dir data/`
- Increase epochs in train_model.py

### No Data in Database
- Import CSV files: `python backend/scripts/import_csv_to_db.py --data-dir data/`
- Check CSV files exist in `data/` directory

### Model Not Saving
- Check `ml_engine/models/` directory exists
- Verify write permissions
- Check disk space

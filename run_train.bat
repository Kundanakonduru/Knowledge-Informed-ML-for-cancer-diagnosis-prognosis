@echo off
REM One-click train: delete old models, recreate CSV, train 96%%+ model, register in DB
cd /d "%~dp0"
echo Running: python ml_engine/train_from_csv.py
python ml_engine/train_from_csv.py
pause

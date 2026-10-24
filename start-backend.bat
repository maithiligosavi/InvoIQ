@echo off
cd /d "%~dp0\backend\venv"
echo Starting DocuFlow Backend Server on http://localhost:8000 ...
.\Scripts\python.exe -m uvicorn main:app --reload --port 8000
pause

@echo off
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  py -3 -m venv .venv
  .venv\Scripts\python.exe -m pip install -r requirements.txt
)
.venv\Scripts\python.exe -m src.pipeline --build-only
start "" http://127.0.0.1:8765
.venv\Scripts\python.exe -m http.server 8765 --bind 127.0.0.1 --directory dist

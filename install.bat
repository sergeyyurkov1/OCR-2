@echo off


cls


call .\venv\Scripts\activate


call .\venv\Scripts\python.exe -m pip install --no-cache-dir -r requirements.txt


pause
Set-Location "C:\Users\PC\Desktop\investment-agent"
.\venv\Scripts\python.exe -m uvicorn backend.api.main:app --host 127.0.0.1 --port 8002

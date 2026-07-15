$Host.UI.RawUI.WindowTitle = "声归 Mock API"
Set-Location -LiteralPath $PSScriptRoot
$env:SHENGGUI_MODEL_BACKEND = "mock"
Write-Host "Starting 声归 FastAPI in MOCK mode..." -ForegroundColor Cyan
Write-Host "Open: http://127.0.0.1:8000" -ForegroundColor Green
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
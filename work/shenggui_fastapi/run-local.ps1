$Host.UI.RawUI.WindowTitle = "声归 Local API"
Set-Location -LiteralPath $PSScriptRoot
$env:SHENGGUI_MODEL_BACKEND = "local"
$env:SHENGGUI_SENSEVOICE_RUNTIME = "llama"
Write-Host "Starting 声归 FastAPI in LOCAL mode..." -ForegroundColor Cyan
Write-Host "SenseVoice needs sensevoice*.gguf under D:\shenggui\SenseVoicePublic or SHENGGUI_SENSEVOICE_GGUF_MODEL." -ForegroundColor Yellow
Write-Host "CosyVoice 3.0 needs runtime dependencies installed in .venv." -ForegroundColor Yellow
Write-Host "Open: http://127.0.0.1:8000" -ForegroundColor Green
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
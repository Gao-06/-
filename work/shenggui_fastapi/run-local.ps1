$Host.UI.RawUI.WindowTitle = "Shenggui Local API"
Set-Location -LiteralPath $PSScriptRoot

$env:SHENGGUI_MODEL_BACKEND = "local"
$env:SHENGGUI_SENSEVOICE_RUNTIME = "llama"

$cosyPython = "D:\shenggui\CosyVoice\cosy_env\Scripts\python.exe"
$projectPython = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
if (Test-Path -LiteralPath $cosyPython) {
    $python = $cosyPython
} else {
    $python = $projectPython
}

Write-Host "Starting Shenggui FastAPI in LOCAL mode..." -ForegroundColor Cyan
Write-Host "Python: $python" -ForegroundColor Cyan
Write-Host "SenseVoice: expects GGUF files under D:\shenggui\SenseVoicePublic." -ForegroundColor Yellow
Write-Host "CosyVoice 3.0: expects repo, weights, dependencies, and third_party\Matcha-TTS." -ForegroundColor Yellow
Write-Host "Open: http://127.0.0.1:8000" -ForegroundColor Green

& $python -m uvicorn app.main:app --host 127.0.0.1 --port 8000

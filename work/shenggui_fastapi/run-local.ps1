param(
    [int]$Port = 8000
)

$Host.UI.RawUI.WindowTitle = "Shenggui Local API"
Set-Location -LiteralPath $PSScriptRoot

$env:SHENGGUI_MODEL_BACKEND = "local"
$env:SHENGGUI_SENSEVOICE_RUNTIME = "llama"

$runtimeRoot = $env:SHENGGUI_RUNTIME_DIR
if ([string]::IsNullOrWhiteSpace($runtimeRoot)) {
    $runtimeRoot = "D:\shenggui\ShengguiRuntime"
}
$env:SHENGGUI_RUNTIME_DIR = $runtimeRoot

$cacheRoot = Join-Path $runtimeRoot "model-cache"
New-Item -ItemType Directory -Force -Path $cacheRoot | Out-Null
$env:HF_HOME = Join-Path $cacheRoot "huggingface"
$env:HF_HUB_CACHE = Join-Path $env:HF_HOME "hub"
$env:MPLCONFIGDIR = Join-Path $cacheRoot "matplotlib"
$env:NUMBA_CACHE_DIR = Join-Path $cacheRoot "numba"
$env:TORCH_HOME = Join-Path $cacheRoot "torch"
$env:TEMP = Join-Path $runtimeRoot "tmp"
$env:TMP = $env:TEMP
$env:TMPDIR = $env:TEMP
New-Item -ItemType Directory -Force -Path $env:HF_HUB_CACHE, $env:MPLCONFIGDIR, $env:NUMBA_CACHE_DIR, $env:TORCH_HOME, $env:TEMP | Out-Null

$cosyPython = "D:\shenggui\CosyVoice\cosy_env\Scripts\python.exe"
$projectPython = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
if (Test-Path -LiteralPath $cosyPython) {
    $python = $cosyPython
} else {
    $python = $projectPython
}

Write-Host "Starting Shenggui FastAPI in LOCAL mode..." -ForegroundColor Cyan
Write-Host "Python: $python" -ForegroundColor Cyan
Write-Host "Runtime: $runtimeRoot" -ForegroundColor Cyan
Write-Host "SenseVoice: expects GGUF files under D:\shenggui\SenseVoicePublic." -ForegroundColor Yellow
Write-Host "CosyVoice 3.0: expects repo, weights, dependencies, and third_party\Matcha-TTS." -ForegroundColor Yellow
Write-Host "Open: http://127.0.0.1:$Port" -ForegroundColor Green

& $python -m uvicorn app.main:app --host 127.0.0.1 --port $Port

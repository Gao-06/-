# 声归 FastAPI MVP

这个目录是“声归”网页原型配套的后端骨架。默认接口运行在 `mock` 模式，方便先调页面、录音、上传和交互流程，不会加载大模型。

## 运行 mock 服务

```powershell
cd "D:\System Data\Desktop\方言\work\shenggui_fastapi"
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
$env:SHENGGUI_MODEL_BACKEND="mock"
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

打开 http://127.0.0.1:8000 即可看到页面。

## 切换 local 模式

local 模式会尝试调用本机模型。当前默认路径已经预留为：

- SenseVoice 引擎目录：`D:\shenggui\SenseVoice`，若不存在会自动使用 `D:\shenggui\SenseVoicePublic`
- SenseVoice 二进制：`llama-funasr-sensevoice.exe`
- CosyVoice 源码：`D:\shenggui\CosyVoice\CosyVoice-main`
- CosyVoice 3.0 权重：`D:\shenggui\CosyVoice\CosyVoice3-5B`

```powershell
$env:SHENGGUI_MODEL_BACKEND="local"
$env:SHENGGUI_SENSEVOICE_RUNTIME="llama"
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

SenseVoicePublic 需要额外有 `sensevoice*.gguf`。如果要启用长音频 VAD，再放入 `*vad*.gguf`，或显式指定：

```powershell
$env:SHENGGUI_SENSEVOICE_GGUF_MODEL="D:\shenggui\SenseVoicePublic\funasr-gguf\sensevoice.gguf"
$env:SHENGGUI_SENSEVOICE_VAD_GGUF="D:\shenggui\SenseVoicePublic\funasr-gguf\fsmn-vad.gguf"
```

## 接口

- `GET /api/health`：模型、路径与服务状态。
- `GET /api/lessons`：情境技能树数据。
- `POST /api/evaluate`：上传练习音频，返回 SenseVoice-Small 风格的评分结构。
- `POST /api/clone-preview`：上传用户参考音频，返回 CosyVoice 3.0 镜像示范结果。

## 模型接入位置

- `app/settings.py`：环境变量和本地绝对路径。
- `app/services/model_adapters.py`：SenseVoice llama-funasr / FunASR 与 CosyVoice 3.0 适配层。
- `app/services/speech.py`：业务服务层，负责把模型结果整理成前端需要的评分和音频返回结构。

当前 MVP 里，SenseVoice-Small 先承担 ASR 识别，评分采用“识别文本 vs 目标文本”的轻量相似度评估。真正的声母、韵母、声调细粒度评价，后续建议再接音素/声调对齐器或训练专项评分模型。

更多本地部署步骤见 [docs/model-integration.md](docs/model-integration.md)。

## 近期更新

- [2026-07-16 本地模型启动与 CosyVoice 依赖检查更新](docs/update-2026-07-16.md)

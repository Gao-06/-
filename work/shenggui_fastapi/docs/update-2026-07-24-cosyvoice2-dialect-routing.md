# 2026-07-24 CosyVoice2 方言模型路由更新

本次更新把音色克隆从单一通用 CosyVoice 模型改为按方言选择 CosyVoice2 微调模型。用户在网页选择某个方言后，`/api/clone-preview` 会读取同一个 `dialect` 参数并调用对应权重。

## 当前支持

| 方言参数 | 页面显示 | 本地模型目录 |
| --- | --- | --- |
| `yue` | 粤语 · 广府片 | `D:\shenggui\CosyVoice2-Yue\pretrained_models\yue\CosyVoice2-Yue-ZoengJyutGaai\CosyVoice2-yue-zjg` |
| `wu` | 吴语 · 苏沪嘉小片 | `D:\shenggui\CosyVoice2-Wu\pretrained_models\ASLP-lab\WenetSpeech-Wu-Speech-Generation\CosyVoice2` |
| `southwest` | 西南官话 · 成渝片 | `D:\shenggui\CosyVoice2-Chuan\pretrained_models\chuan\CosyVoice2-Chuan` |

闽南语暂时没有对应微调模型，本次已从网页下拉选择、前端课程数据和后端课程库中移除，也不再保留对应的音色克隆调用入口。

## 后端行为

- `app/settings.py` 新增 `VoiceCloneProfile`，集中描述每个方言对应的模型目录、显示名称和 readiness。
- `app/services/model_adapters.py` 的 `CosyVoiceAdapter` 改为单活跃模型加载：切换方言时先卸载上一套模型，再加载当前方言模型，避免同时占用多套模型内存。
- `GET /api/health` 的 `models.voice_clone.profiles` 会返回三套方言模型的路径、ready 状态和当前 loaded 状态。
- `/api/clone-preview` 的响应新增 `voice_model`，前端和调试人员可以看到本次请求实际选中的模型、模型目录、是否 ready、是否 loaded。
- 短录音仍统一返回 `voice_too_short`，前端展示“说话时间太短了，无法生成，请至少说 10 秒。”

## 环境变量覆盖

如果本机模型目录与默认路径不同，可以通过环境变量覆盖：

| 变量 | 作用 |
| --- | --- |
| `SHENGGUI_COSYVOICE_YUE_MODEL_DIR` | 粤语音色克隆微调模型目录 |
| `SHENGGUI_COSYVOICE_WU_MODEL_DIR` | 吴语音色克隆微调模型目录 |
| `SHENGGUI_COSYVOICE_CHUAN_MODEL_DIR` | 西南官话/川渝音色克隆微调模型目录 |
| `SHENGGUI_COSYVOICE_REPO` | CosyVoice 源码目录，用于加载 `cosyvoice.cli.cosyvoice.AutoModel` |

`SHENGGUI_COSYVOICE_MODEL_DIR` 不再作为音色克隆的单一模型入口使用。

## 前端变化

- 方言选择器保留粤语、吴语、西南官话，移除暂未接入微调模型的闽南语。
- 页面模型标识从通用 `CosyVoice 3.0` 调整为 `CosyVoice2 方言微调`。
- 切换方言时，录音提示会显示当前将使用的方言专用模型。
- 音色克隆区域继续强调“镜像跟读”，标准发音仍以母语者示范为准。

## 验证建议

启动 local 服务后检查：

```powershell
Invoke-RestMethod http://127.0.0.1:8000/api/health |
    ConvertTo-Json -Depth 8
```

重点确认：

- `models.voice_clone.profiles.yue.model_dir` 指向粤语模型目录。
- `models.voice_clone.profiles.wu.model_dir` 指向吴语模型目录。
- `models.voice_clone.profiles.southwest.model_dir` 指向西南官话模型目录。
- 对应模型目录存在时，`ready` 为 `true`。
- 完成一次生成后，当前方言 profile 的 `loaded` 为 `true`。

基础代码校验：

```powershell
.\.venv\Scripts\python.exe -m compileall -q app
```

## 注意事项

- 目前模型是单活跃加载，不会同时常驻三套 CosyVoice2 权重；首次切换到某个方言时可能会有模型加载耗时。
- 如果用户请求不支持的方言，接口会返回 400，并提示暂不支持该方言。
- 生成音频仍写入 `static/generated` 供前端播放，该目录由 `.gitignore` 排除，不进入版本库。

# 2026-07-16 双模型接通与音色克隆错误提示更新

## 更新背景

本次更新围绕 local 模式的真实模型联调展开：一条链路接入 SenseVoice-Small 语音识别与评分，另一条链路接入 CosyVoice 3.0 音色克隆生成。与此同时，音色克隆阶段常见的底层异常不再直接暴露给用户，而是转换成更容易理解和处理的中文提示。

## 已接通的模型链路

### 1. SenseVoice-Small 评测链路

`/api/evaluate` 在 local 模式下会调用 SenseVoice 识别用户上传的练习音频，再把识别文本与目标句子做轻量相似度评估，返回 MVP 阶段的评分、标题、建议和分项指标。

当前优先使用 `llama-funasr-sensevoice.exe` 路线，默认从 `D:\shenggui\SenseVoicePublic` 发现二进制与 `sensevoice*.gguf` 权重。浏览器录音应上传 WAV、MP3 或 FLAC，避免把 WebM 直接交给本地 llama-funasr 运行时。

### 2. CosyVoice 3.0 音色克隆链路

`/api/clone-preview` 在 local 模式下会调用 CosyVoice 3.0 的 zero-shot 推理，使用用户参考音频生成同音色的镜像跟读音频。标准发音仍以母语者示范音频为准，CosyVoice 生成结果主要用于降低用户对自身口音练习的距离感。

本次补齐了 CosyVoice 3.0 的提示词格式处理：如果权重目录存在 `cosyvoice3.yaml`，后端会自动为 prompt 增加 CosyVoice 3.0 需要的 `<|endofprompt|>` 前缀格式，避免直接把普通文本交给模型导致推理异常。

## 运行目录与缓存调整

模型运行过程中产生的缓存、临时文件和中间音频现在集中放到运行目录，默认是：

```text
D:\shenggui\ShengguiRuntime\
  model-cache\
    huggingface\
    matplotlib\
    numba\
    torch\
  tmp\
  audio\
    prompt\
    generated\
```

相关环境变量包括：

- `SHENGGUI_RUNTIME_DIR`：运行目录根路径，默认 `D:\shenggui\ShengguiRuntime`。
- `SHENGGUI_CACHE_DIR`：模型缓存目录，默认 `<runtime>\model-cache`。
- `HF_HOME` / `HF_HUB_CACHE`：Hugging Face 缓存目录。
- `MPLCONFIGDIR`：Matplotlib 配置缓存目录。
- `NUMBA_CACHE_DIR`：Numba 缓存目录。
- `TORCH_HOME`：Torch 缓存目录。
- `TEMP` / `TMP` / `TMPDIR`：模型临时文件目录。

CosyVoice 生成音频时，后端会先把中间产物写入运行目录，再复制一份到 `static/generated` 供前端播放。中间产物会在请求结束后清理，前端可访问的 WAV 文件继续由 `.gitignore` 排除，不进入版本库。

## 音色克隆错误提示优化

音色克隆接口新增了更明确的业务状态，前端会根据状态显示简短结果：

| 状态 | 用户提示 | 典型原因 | 建议处理 |
| --- | --- | --- | --- |
| `generated` | 已生成 | CosyVoice 成功返回示范音频 | 播放生成结果 |
| `voice_too_short` | 说话时间太短了 | 参考录音不足 10 秒，或底层卷积报错指向音频过短 | 重新录制 10 秒以上、连续清晰的语音 |
| `audio_read_failed` | 录音文件读取失败 | 后端或模型无法读取上传音频 | 重新录制 WAV 音频后再生成 |
| `model_env_error` | 本地音色模型环境异常 | 权重已找到，但 Python/依赖环境与 CosyVoice 不匹配 | 使用 CosyVoice 专用 Python 环境启动后端 |
| `mock_ready` | 本地模拟 | mock 回退或未收到参考音频 | 检查 local 依赖与音频输入 |

底层异常仍会写入后端日志，方便开发排查；接口响应则尽量返回用户能直接理解和行动的中文文案。

## 前端呈现调整

- 页面模型标识从 `CosyVoice 2` 更新为 `CosyVoice 3.0`。
- 音色克隆区域从“用户音色标准示范”改为“用户音色镜像跟读”，避免把克隆音频误表达为权威标准发音。
- 母语者示范按钮新增“示范待上传”状态；当前没有本土母语者素材时，会提示后续需要接入真实录音。
- 音色克隆结果会根据后端状态显示 `已生成`、`需重录`、`环境异常` 或 `本地模拟`，用户不需要阅读底层错误堆栈。

## 启动方式

local 模式启动脚本现在支持端口参数，并会自动设置模型运行目录和缓存环境变量：

```powershell
.\run-local.ps1 -Port 8000
```

启动时终端会打印：

- 实际使用的 Python。
- 运行目录 `Runtime`。
- SenseVoice 与 CosyVoice 的必要依赖提醒。
- 访问地址。

## 验证建议

基础校验：

```powershell
.\.venv\Scripts\python.exe -m compileall -q app
```

接口校验：

```powershell
Invoke-RestMethod http://127.0.0.1:8000/api/health |
    ConvertTo-Json -Depth 6
```

音色克隆校验：

1. 上传少于 10 秒的 WAV，确认返回 `voice_too_short`。
2. 上传 10 秒以上、连续清晰的 WAV，确认 CosyVoice 能生成 `audio_url`。
3. 如果返回 `model_env_error`，优先确认启动脚本使用的是 `D:\shenggui\CosyVoice\cosy_env\Scripts\python.exe`。

## 影响范围

- mock 模式继续可用。
- `/api/evaluate` 和 `/api/clone-preview` 的返回结构保持前端可消费。
- 新增的错误状态会让前端显示更贴近用户操作的提示。
- 生成音频和运行缓存仍是本地运行产物，不应提交到 Git。

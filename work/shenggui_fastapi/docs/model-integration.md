# 声归后端模型接入设计

## 权限边界

Codex 可以直接完成后端代码、接口设计、适配层、配置和文档。下载 SenseVoice GGUF 权重、安装 PyTorch/CUDA/CosyVoice 相关依赖、联网拉包时，需要你授权命令，或者手动把模型与依赖放到本机路径。

## 后端分层

- `app/main.py`：FastAPI 路由层，只处理请求参数、文件上传和响应；模型推理通过线程池执行，避免阻塞事件循环。
- `app/services/speech.py`：业务服务层，统一输出前端需要的评分、建议、镜像示范音频地址。
- `app/services/model_adapters.py`：模型适配层，隔离 SenseVoice llama-funasr / FunASR / CosyVoice 的具体调用。
- `app/settings.py`：运行配置，默认 mock，可通过环境变量切到本地模型。

## 环境变量

| 变量 | 默认值 | 作用 |
| --- | --- | --- |
| `SHENGGUI_MODEL_BACKEND` | `mock` | `mock` 不加载模型，`local` 加载本地模型 |
| `SHENGGUI_MODEL_FALLBACK_TO_MOCK` | `true` | 本地模型报错时是否回退模拟响应 |
| `SHENGGUI_MODEL_DEVICE` | `cpu` | FunASR/PyTorch 路线使用，`cpu` 或 `cuda:0` |
| `SHENGGUI_SENSEVOICE_RUNTIME` | `llama` | `llama` 使用 SenseVoicePublic 二进制；其他值走 FunASR Python |
| `SHENGGUI_SENSEVOICE_ENGINE_DIR` | `D:\shenggui\SenseVoice` | SenseVoice 引擎目录；不存在时自动尝试 `D:\shenggui\SenseVoicePublic` |
| `SHENGGUI_SENSEVOICE_BINARY_NAME` | `llama-funasr-sensevoice.exe` | SenseVoicePublic 可执行文件名 |
| `SHENGGUI_SENSEVOICE_GGUF_MODEL` | 自动发现 | SenseVoice GGUF 权重路径 |
| `SHENGGUI_SENSEVOICE_VAD_GGUF` | 自动发现 | FSMN-VAD GGUF 权重路径，可为空 |
| `SHENGGUI_SENSEVOICE_TIMEOUT_SECONDS` | `60` | llama-funasr 单次识别超时 |
| `SHENGGUI_COSYVOICE_REPO` | `D:\shenggui\CosyVoice\CosyVoice-main` | CosyVoice 3.0 源码目录 |
| `SHENGGUI_COSYVOICE_MODEL_DIR` | `D:\shenggui\CosyVoice\CosyVoice3-5B` | CosyVoice 3.0 权重目录 |

## SenseVoice-Small 接入

当前优先支持你本机的 `SenseVoicePublic` 路线：

```text
D:\shenggui\SenseVoicePublic\
  llama-funasr-sensevoice.exe
  sensevoice*.gguf
  fsmn-vad*.gguf  # 可选
```

`llama-funasr-sensevoice.exe --help` 显示其调用格式为：

```text
llama-funasr-sensevoice.exe -m sensevoice.gguf -a audio.wav [--vad fsmn-vad.gguf]
```

所以前端录音已改为优先上传 WAV。当前你的 `SenseVoicePublic` 目录里只有二进制，还没有 `.gguf` 权重；local 模式下如果上传音频，会返回“缺少 SenseVoice GGUF 模型”的清晰错误，并在 `SHENGGUI_MODEL_FALLBACK_TO_MOCK=true` 时回退 mock。

如果你后续改用 FunASR Python 路线，可以设置：

```powershell
$env:SHENGGUI_SENSEVOICE_RUNTIME="funasr"
$env:SHENGGUI_SENSEVOICE_MODEL="iic/SenseVoiceSmall"
```

并安装对应依赖：`funasr modelscope torch torchaudio`。

## CosyVoice 3.0 接入

当前默认指向：

```text
D:\shenggui\CosyVoice\
  CosyVoice-main\
  CosyVoice3-5B\
    cosyvoice3.yaml
    llm.pt
    flow.pt
    hift.pt
    speech_tokenizer_v3.onnx
```

适配层会把 `CosyVoice-main` 和 `third_party\Matcha-TTS` 加入 `sys.path`，再调用源码里的 `AutoModel(model_dir=...)`。`AutoModel` 会根据权重目录中的 `cosyvoice3.yaml` 自动实例化 CosyVoice3。

注意：目前项目虚拟环境只安装了 FastAPI 基础依赖。要真正生成音频，还需要安装 CosyVoice 的运行依赖，尤其是 `torch`、`torchaudio`、`modelscope`、`HyperPyYAML`、`onnxruntime`、`transformers` 等。建议后续单独做一次“CosyVoice 依赖安装与 GPU/CPU 验证”，不要和 mock 服务调试混在一起。

## 推荐实施顺序

1. 继续保持 `mock` 模式，把页面、录音、上传、接口返回结构调顺。
2. 下载或放置 SenseVoice GGUF 权重，验证 `/api/evaluate` 的 local ASR。
3. 安装 CosyVoice 3.0 运行依赖，验证 `/api/clone-preview` 生成短句 WAV。
4. 收集母语者音频素材，补充“原真示范音频库”接口。
5. 再设计细粒度发音评价：音素/声调对齐、方言音系规则、错误标签和针对性练习。
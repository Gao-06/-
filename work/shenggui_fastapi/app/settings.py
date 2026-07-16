from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
PROJECT_DIR = BASE_DIR.parent
STATIC_DIR = PROJECT_DIR / "static"
GENERATED_AUDIO_DIR = STATIC_DIR / "generated"
DEFAULT_RUNTIME_DIR = Path(r"D:\shenggui\ShengguiRuntime")
RUNTIME_DIR = Path(os.getenv("SHENGGUI_RUNTIME_DIR", str(DEFAULT_RUNTIME_DIR)))
CACHE_DIR = Path(os.getenv("SHENGGUI_CACHE_DIR", str(RUNTIME_DIR / "model-cache")))
RUNTIME_TMP_DIR = RUNTIME_DIR / "tmp"
RUNTIME_AUDIO_DIR = RUNTIME_DIR / "audio"

CACHE_DIR.mkdir(parents=True, exist_ok=True)
(CACHE_DIR / "huggingface").mkdir(parents=True, exist_ok=True)
(CACHE_DIR / "matplotlib").mkdir(parents=True, exist_ok=True)
(CACHE_DIR / "numba").mkdir(parents=True, exist_ok=True)
(CACHE_DIR / "torch").mkdir(parents=True, exist_ok=True)
RUNTIME_TMP_DIR.mkdir(parents=True, exist_ok=True)
RUNTIME_AUDIO_DIR.mkdir(parents=True, exist_ok=True)
os.environ.setdefault("HF_HOME", str(CACHE_DIR / "huggingface"))
os.environ.setdefault("HF_HUB_CACHE", str(CACHE_DIR / "huggingface" / "hub"))
os.environ.setdefault("MPLCONFIGDIR", str(CACHE_DIR / "matplotlib"))
os.environ.setdefault("TORCH_HOME", str(CACHE_DIR / "torch"))
os.environ["NUMBA_CACHE_DIR"] = str(CACHE_DIR / "numba")
os.environ["TEMP"] = str(RUNTIME_TMP_DIR)
os.environ["TMP"] = str(RUNTIME_TMP_DIR)
os.environ["TMPDIR"] = str(RUNTIME_TMP_DIR)

DEFAULT_SENSEVOICE_ENGINE_DIR = Path(r"D:\shenggui\SenseVoice")
DEFAULT_SENSEVOICE_PUBLIC_DIR = Path(r"D:\shenggui\SenseVoicePublic")
DEFAULT_COSYVOICE_REPO = Path(r"D:\shenggui\CosyVoice\CosyVoice-main")
DEFAULT_COSYVOICE_MODEL_DIR = Path(r"D:\shenggui\CosyVoice\CosyVoice3-5B")


def _get_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _get_int(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None:
        return default
    return int(value)


def _find_gguf(root: Path, *, include: tuple[str, ...], exclude: tuple[str, ...] = ()) -> Path | None:
    if not root.exists():
        return None
    try:
        candidates = sorted(root.rglob("*.gguf"))
    except OSError:
        return None
    for path in candidates:
        lower_name = path.name.lower()
        if all(part in lower_name for part in include) and not any(part in lower_name for part in exclude):
            return path
    return None


@dataclass(frozen=True)
class Settings:
    model_backend: str = os.getenv("SHENGGUI_MODEL_BACKEND", "mock").strip().lower()
    model_fallback_to_mock: bool = _get_bool("SHENGGUI_MODEL_FALLBACK_TO_MOCK", True)
    device: str = os.getenv("SHENGGUI_MODEL_DEVICE", "cpu")

    sensevoice_runtime: str = os.getenv("SHENGGUI_SENSEVOICE_RUNTIME", "llama").strip().lower()
    sensevoice_engine_root: str = os.getenv(
        "SHENGGUI_SENSEVOICE_ENGINE_DIR",
        str(DEFAULT_SENSEVOICE_ENGINE_DIR),
    )
    sensevoice_binary_name: str = os.getenv(
        "SHENGGUI_SENSEVOICE_BINARY_NAME",
        "llama-funasr-sensevoice.exe",
    )
    sensevoice_gguf_model: str | None = os.getenv("SHENGGUI_SENSEVOICE_GGUF_MODEL")
    sensevoice_vad_gguf: str | None = os.getenv("SHENGGUI_SENSEVOICE_VAD_GGUF")
    sensevoice_timeout_seconds: int = _get_int("SHENGGUI_SENSEVOICE_TIMEOUT_SECONDS", 60)

    sensevoice_model: str = os.getenv("SHENGGUI_SENSEVOICE_MODEL", "iic/SenseVoiceSmall")
    sensevoice_remote_code: str | None = os.getenv("SHENGGUI_SENSEVOICE_REMOTE_CODE")
    sensevoice_vad_model: str | None = os.getenv("SHENGGUI_SENSEVOICE_VAD_MODEL", "fsmn-vad")
    sensevoice_max_segment_ms: int = _get_int("SHENGGUI_SENSEVOICE_MAX_SEGMENT_MS", 30000)

    cosyvoice_repo: str | None = os.getenv("SHENGGUI_COSYVOICE_REPO", str(DEFAULT_COSYVOICE_REPO))
    cosyvoice_model_dir: str = os.getenv(
        "SHENGGUI_COSYVOICE_MODEL_DIR",
        str(DEFAULT_COSYVOICE_MODEL_DIR),
    )
    cosyvoice_audio_dir: Path = RUNTIME_AUDIO_DIR
    generated_audio_dir: Path = GENERATED_AUDIO_DIR

    @property
    def sensevoice_engine_dir(self) -> Path:
        configured = Path(self.sensevoice_engine_root)
        if configured.exists():
            return configured
        if DEFAULT_SENSEVOICE_PUBLIC_DIR.exists():
            return DEFAULT_SENSEVOICE_PUBLIC_DIR
        return configured

    @property
    def sensevoice_binary(self) -> Path:
        return self.sensevoice_engine_dir / self.sensevoice_binary_name

    @property
    def sensevoice_gguf_model_path(self) -> Path | None:
        if self.sensevoice_gguf_model:
            return Path(self.sensevoice_gguf_model)
        return _find_gguf(
            self.sensevoice_engine_dir,
            include=("sensevoice",),
            exclude=("vad", "fsmn"),
        )

    @property
    def sensevoice_vad_gguf_path(self) -> Path | None:
        if self.sensevoice_vad_gguf:
            return Path(self.sensevoice_vad_gguf)
        return _find_gguf(
            self.sensevoice_engine_dir,
            include=("vad",),
        )

    @property
    def use_local_models(self) -> bool:
        return self.model_backend == "local"


settings = Settings()

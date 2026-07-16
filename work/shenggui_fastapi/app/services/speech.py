from __future__ import annotations

import io
import logging
import wave
from dataclasses import dataclass

from ..settings import settings
from .library import DIALECT_LIBRARY, get_scene_data
from .model_adapters import (
    CosyVoiceAdapter,
    SenseVoiceSmallAdapter,
    build_assessment_from_text,
)


MIN_VOICE_CLONE_SECONDS = 10.0
_SHORT_AUDIO_ERROR_MARKERS = (
    "Calculated padded input size per channel",
    "Kernel size can't be greater than actual input size",
)
_AUDIO_IO_ERROR_MARKERS = (
    "[Errno 22] Invalid argument",
    "Invalid argument",
    "Error opening",
    "Failed to open",
)
_MODEL_ENV_ERROR_MARKERS = (
    "Cannot copy out of meta tensor",
    "Module.to_empty()",
)
logger = logging.getLogger(__name__)


def _wav_duration_seconds(audio_bytes: bytes) -> float | None:
    if not audio_bytes:
        return None

    try:
        with wave.open(io.BytesIO(audio_bytes), "rb") as wav_file:
            frame_rate = wav_file.getframerate()
            if frame_rate <= 0:
                return None
            return wav_file.getnframes() / float(frame_rate)
    except (EOFError, ValueError, wave.Error):
        return None


def _looks_like_short_audio_error(error: str) -> bool:
    return any(marker in error for marker in _SHORT_AUDIO_ERROR_MARKERS)


def _looks_like_audio_io_error(error: str) -> bool:
    return any(marker in error for marker in _AUDIO_IO_ERROR_MARKERS)


def _looks_like_model_env_error(error: str) -> bool:
    return any(marker in error for marker in _MODEL_ENV_ERROR_MARKERS)


@dataclass(frozen=True)
class SpeechAssessmentService:
    model_name: str = "SenseVoice-Small"

    def __post_init__(self) -> None:
        object.__setattr__(self, "_adapter", SenseVoiceSmallAdapter(settings))

    @property
    def model_ready(self) -> bool:
        return bool(settings.use_local_models and self._adapter.ready)

    def evaluate(
        self,
        dialect: str,
        scene: str,
        stage: str,
        audio_bytes: bytes,
        filename: str | None = None,
    ) -> dict[str, object]:
        scene_data = get_scene_data(dialect=dialect, scene=scene)
        if settings.use_local_models:
            try:
                recognized_text = self._adapter.transcribe(
                    audio_bytes=audio_bytes,
                    filename=filename,
                    dialect=dialect,
                )
                assessment = build_assessment_from_text(
                    target_text=scene_data["target_text"],
                    recognized_text=recognized_text,
                )
                return {
                    "model": self.model_name,
                    "model_ready": self.model_ready,
                    "backend": settings.model_backend,
                    "dialect": dialect,
                    "scene": scene,
                    "stage": stage,
                    "target_text": scene_data["target_text"],
                    **assessment,
                }
            except Exception as exc:
                if not settings.model_fallback_to_mock:
                    raise
                return self._mock_response(
                    dialect=dialect,
                    scene=scene,
                    stage=stage,
                    scene_data=scene_data,
                    error=str(exc),
                )

        return self._mock_response(
            dialect=dialect,
            scene=scene,
            stage=stage,
            scene_data=scene_data,
        )

    def _mock_response(
        self,
        *,
        dialect: str,
        scene: str,
        stage: str,
        scene_data: dict[str, str],
        error: str | None = None,
    ) -> dict[str, object]:
        title = "尚未接入真实模型"
        advice = (
            "当前 FastAPI 接口运行在 mock 模式，还没有加载 SenseVoice-Small。"
            "接入后会先做 ASR 识别，再基于目标文本输出 MVP 评分。"
        )
        if error:
            title = "本地模型加载失败，已回退模拟结果"
            advice = f"后端尝试调用 SenseVoice-Small 时出错：{error}"
        return {
            "model": self.model_name,
            "model_ready": False,
            "backend": settings.model_backend,
            "dialect": dialect,
            "scene": scene,
            "stage": stage,
            "target_text": scene_data["target_text"],
            "score": 0,
            "title": title,
            "advice": advice,
            "recognized_text": "",
            "metrics": {
                "initial": 0,
                "final": 0,
                "tone": 0,
                "flow": 0,
            },
        }


@dataclass(frozen=True)
class VoiceCloneService:
    model_name: str = "CosyVoice 3.0"

    def __post_init__(self) -> None:
        object.__setattr__(self, "_adapter", CosyVoiceAdapter(settings))

    @property
    def model_ready(self) -> bool:
        return bool(settings.use_local_models and self._adapter.ready)

    def create_preview(
        self,
        dialect: str,
        scene: str,
        speaker_audio: bytes,
        filename: str | None = None,
        prompt_text: str | None = None,
    ) -> dict[str, object]:
        scene_data = get_scene_data(dialect=dialect, scene=scene)
        has_voice = len(speaker_audio) > 0
        prompt = prompt_text or scene_data["target_text"]
        duration_seconds = _wav_duration_seconds(speaker_audio) if has_voice else None

        if settings.use_local_models and has_voice:
            if duration_seconds is not None and duration_seconds < MIN_VOICE_CLONE_SECONDS:
                return self._short_audio_response(
                    dialect=dialect,
                    scene_data=scene_data,
                    prompt=prompt,
                    duration_seconds=duration_seconds,
                )

            try:
                audio_url = self._adapter.synthesize_zero_shot(
                    target_text=scene_data["target_text"],
                    prompt_text=prompt,
                    speaker_audio=speaker_audio,
                    filename=filename,
                )
                return {
                    "model": self.model_name,
                    "model_ready": self.model_ready,
                    "backend": settings.model_backend,
                    "dialect": dialect,
                    "status": "generated",
                    "title": "用户音色镜像跟读（实验）",
                    "message": f"已生成“{scene_data['name']}”的用户音色镜像音频；当前效果仅供跟读参考，标准发音以母语者示范为准。",
                    "audio_url": audio_url,
                    "target_text": scene_data["target_text"],
                    "prompt_text": prompt,
                }
            except Exception as exc:
                error = str(exc)
                logger.exception("CosyVoice zero-shot synthesis failed")
                if _looks_like_short_audio_error(error):
                    return self._short_audio_response(
                        dialect=dialect,
                        scene_data=scene_data,
                        prompt=prompt,
                        duration_seconds=duration_seconds,
                    )
                if _looks_like_audio_io_error(error):
                    return self._audio_io_error_response(
                        dialect=dialect,
                        scene_data=scene_data,
                        prompt=prompt,
                        duration_seconds=duration_seconds,
                    )
                if _looks_like_model_env_error(error):
                    return self._model_env_error_response(
                        dialect=dialect,
                        scene_data=scene_data,
                        prompt=prompt,
                    )
                if not settings.model_fallback_to_mock:
                    raise
                return self._mock_response(
                    dialect=dialect,
                    scene_data=scene_data,
                    has_voice=has_voice,
                    prompt=prompt,
                    error=error,
                )

        return self._mock_response(
            dialect=dialect,
            scene_data=scene_data,
            has_voice=has_voice,
            prompt=prompt,
        )

    def _short_audio_response(
        self,
        *,
        dialect: str,
        scene_data: dict[str, str],
        prompt: str,
        duration_seconds: float | None,
    ) -> dict[str, object]:
        return {
            "model": self.model_name,
            "model_ready": self.model_ready,
            "backend": settings.model_backend,
            "dialect": dialect,
            "status": "voice_too_short",
            "title": "说话时间太短了",
            "message": "说话时间太短了，无法生成，请至少说 10 秒，并尽量保持连续、清晰的自然语音。",
            "audio_url": None,
            "target_text": scene_data["target_text"],
            "prompt_text": prompt,
            "min_duration_seconds": MIN_VOICE_CLONE_SECONDS,
            "duration_seconds": round(duration_seconds, 2) if duration_seconds is not None else None,
        }

    def _model_env_error_response(
        self,
        *,
        dialect: str,
        scene_data: dict[str, str],
        prompt: str,
    ) -> dict[str, object]:
        return {
            "model": self.model_name,
            "model_ready": False,
            "backend": settings.model_backend,
            "dialect": dialect,
            "status": "model_env_error",
            "title": "本地音色模型环境异常",
            "message": "CosyVoice 3.0 权重已找到，但模型加载环境不匹配。请确认使用 CosyVoice 专用 Python 环境启动后端。",
            "audio_url": None,
            "target_text": scene_data["target_text"],
            "prompt_text": prompt,
        }

    def _audio_io_error_response(
        self,
        *,
        dialect: str,
        scene_data: dict[str, str],
        prompt: str,
        duration_seconds: float | None,
    ) -> dict[str, object]:
        return {
            "model": self.model_name,
            "model_ready": self.model_ready,
            "backend": settings.model_backend,
            "dialect": dialect,
            "status": "audio_read_failed",
            "title": "录音文件读取失败",
            "message": "后端读取录音文件失败。请重新录制一段 10 秒以上、连续清晰的语音后再生成。",
            "audio_url": None,
            "target_text": scene_data["target_text"],
            "prompt_text": prompt,
            "duration_seconds": round(duration_seconds, 2) if duration_seconds is not None else None,
        }

    def _mock_response(
        self,
        *,
        dialect: str,
        scene_data: dict[str, str],
        has_voice: bool,
        prompt: str,
        error: str | None = None,
    ) -> dict[str, object]:
        title = "用户音色镜像跟读（实验）" if has_voice else "等待用户音色样本"
        message = (
            f"已为“{scene_data['name']}”生成模拟任务。接入 CosyVoice 3.0 后返回用户音色镜像跟读；标准发音以母语者示范为准。"
            if has_voice
            else "当前没有收到音色样本；真实服务会要求一段用户参考音频。"
        )
        if error:
            title = "本地音色模型加载失败，已回退模拟结果"
            message = f"后端尝试调用 CosyVoice 3.0 时出错：{error}"
        return {
            "model": self.model_name,
            "model_ready": False,
            "backend": settings.model_backend,
            "dialect": dialect,
            "status": "mock_ready",
            "title": title,
            "message": message,
            "audio_url": None,
            "target_text": scene_data["target_text"],
            "prompt_text": prompt,
        }

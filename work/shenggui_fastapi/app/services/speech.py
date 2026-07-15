from __future__ import annotations

from dataclasses import dataclass

from ..settings import settings
from .library import DIALECT_LIBRARY, get_scene_data
from .model_adapters import (
    CosyVoiceAdapter,
    SenseVoiceSmallAdapter,
    build_assessment_from_text,
)


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

        if settings.use_local_models and has_voice:
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
                    "title": "用户音色标准示范",
                    "message": f"已生成“{scene_data['name']}”的同音色标准方言音频。",
                    "audio_url": audio_url,
                    "target_text": scene_data["target_text"],
                    "prompt_text": prompt,
                }
            except Exception as exc:
                if not settings.model_fallback_to_mock:
                    raise
                return self._mock_response(
                    dialect=dialect,
                    scene_data=scene_data,
                    has_voice=has_voice,
                    prompt=prompt,
                    error=str(exc),
                )

        return self._mock_response(
            dialect=dialect,
            scene_data=scene_data,
            has_voice=has_voice,
            prompt=prompt,
        )

    def _mock_response(
        self,
        *,
        dialect: str,
        scene_data: dict[str, str],
        has_voice: bool,
        prompt: str,
        error: str | None = None,
    ) -> dict[str, object]:
        title = "用户音色标准示范" if has_voice else "等待用户音色样本"
        message = (
            f"已为“{scene_data['name']}”生成模拟任务。接入 CosyVoice 3.0 后返回同音色标准方言音频。"
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

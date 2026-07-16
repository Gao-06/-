from __future__ import annotations

import re
import shutil
import subprocess
import sys
import tempfile
import uuid
from difflib import SequenceMatcher
from importlib.util import find_spec
from pathlib import Path
from typing import Any

from ..settings import Settings


DIALECT_TO_SENSEVOICE_LANGUAGE = {
    "yue": "yue",
    "wu": "zh",
    "minnan": "zh",
    "southwest": "zh",
}

LLAMA_FUNASR_AUDIO_SUFFIXES = {".wav", ".mp3", ".flac"}
SENSEVOICE_TAG_RE = re.compile(r"<\|[^>]+\|>")
ANSI_RE = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")


def _safe_suffix(filename: str | None, default: str) -> str:
    suffix = Path(filename or "").suffix.lower()
    return suffix if suffix else default


def _write_temp_audio(
    audio_bytes: bytes,
    filename: str | None,
    default_suffix: str,
    directory: Path | None = None,
) -> Path:
    suffix = _safe_suffix(filename=filename, default=default_suffix)
    if directory is not None:
        directory.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        delete=False,
        suffix=suffix,
        dir=str(directory) if directory is not None else None,
    ) as temp_file:
        temp_file.write(audio_bytes)
        return Path(temp_file.name)


def _format_cosyvoice3_prompt(prompt_text: str) -> str:
    if "<|endofprompt|>" in prompt_text:
        return prompt_text
    return f"You are a helpful assistant.<|endofprompt|>{prompt_text}"


def text_similarity(expected: str, actual: str) -> float:
    return SequenceMatcher(None, expected, actual).ratio()


def build_assessment_from_text(target_text: str, recognized_text: str) -> dict[str, object]:
    similarity = text_similarity(target_text, recognized_text)
    score = round(45 + similarity * 50)
    score = max(0, min(100, score))

    tone = max(0, min(100, score - 4))
    flow = max(0, min(100, score - 2))
    initial = max(0, min(100, score + 3))
    final = max(0, min(100, score))

    if score >= 88:
        title = "识别文本高度匹配"
        advice = "整句内容已经比较稳定，下一步建议增加真实语速和情绪表达。"
    elif score >= 72:
        title = "核心内容基本匹配"
        advice = "SenseVoice 已能识别出大部分内容，可继续针对连读和尾音做慢速复述。"
    else:
        title = "识别偏差较明显"
        advice = "建议先跟读母语者示范，缩短句子，只练核心语块后再合成整句。"

    return {
        "score": score,
        "title": title,
        "advice": advice,
        "recognized_text": recognized_text,
        "metrics": {
            "initial": initial,
            "final": final,
            "tone": tone,
            "flow": flow,
        },
    }


def _clean_sensevoice_output(stdout: str) -> str:
    text = ANSI_RE.sub("", stdout).replace("\r", "\n")
    lines = [line.strip() for line in text.split("\n") if line.strip()]
    if not lines:
        return ""

    # llama-funasr usually prints diagnostics before the final recognition line.
    candidate = lines[-1]
    for line in reversed(lines):
        lower = line.lower()
        if not any(marker in lower for marker in ("usage:", "main:", "system_info", "load_")):
            candidate = line
            break
    candidate = SENSEVOICE_TAG_RE.sub("", candidate)
    if ":" in candidate:
        prefix, rest = candidate.split(":", 1)
        if len(prefix) <= 32 and any(ch.isalpha() for ch in prefix):
            candidate = rest
    return candidate.strip()


class SenseVoiceSmallAdapter:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._model: Any | None = None
        self._postprocess: Any | None = None

    @property
    def ready(self) -> bool:
        if self.settings.sensevoice_runtime == "llama":
            model_path = self.settings.sensevoice_gguf_model_path
            return bool(self.settings.sensevoice_binary.exists() and model_path and model_path.exists())
        return self._model is not None

    def _load_fun_asr(self) -> None:
        if self._model is not None:
            return

        from funasr import AutoModel
        from funasr.utils.postprocess_utils import rich_transcription_postprocess

        kwargs: dict[str, Any] = {
            "model": self.settings.sensevoice_model,
            "trust_remote_code": True,
            "device": self.settings.device,
        }
        if self.settings.sensevoice_remote_code:
            kwargs["remote_code"] = self.settings.sensevoice_remote_code
        if self.settings.sensevoice_vad_model:
            kwargs["vad_model"] = self.settings.sensevoice_vad_model
            kwargs["vad_kwargs"] = {
                "max_single_segment_time": self.settings.sensevoice_max_segment_ms,
            }

        self._model = AutoModel(**kwargs)
        self._postprocess = rich_transcription_postprocess

    def transcribe(
        self,
        *,
        audio_bytes: bytes,
        filename: str | None,
        dialect: str,
    ) -> str:
        if not audio_bytes:
            return ""
        if self.settings.sensevoice_runtime == "llama":
            return self._transcribe_with_llama(audio_bytes=audio_bytes, filename=filename)
        return self._transcribe_with_funasr(
            audio_bytes=audio_bytes,
            filename=filename,
            dialect=dialect,
        )

    def _transcribe_with_llama(self, *, audio_bytes: bytes, filename: str | None) -> str:
        binary = self.settings.sensevoice_binary
        model_path = self.settings.sensevoice_gguf_model_path
        vad_path = self.settings.sensevoice_vad_gguf_path

        if not binary.exists():
            raise RuntimeError(f"SenseVoice binary not found: {binary}")
        if model_path is None or not model_path.exists():
            raise RuntimeError(
                "SenseVoice GGUF model not found. Put sensevoice*.gguf under "
                f"{self.settings.sensevoice_engine_dir} or set SHENGGUI_SENSEVOICE_GGUF_MODEL."
            )

        suffix = _safe_suffix(filename=filename, default=".wav")
        if suffix not in LLAMA_FUNASR_AUDIO_SUFFIXES:
            raise RuntimeError(
                "llama-funasr SenseVoice accepts wav/mp3/flac. "
                f"Received {suffix or 'unknown'}; convert browser webm to wav before local ASR."
            )

        audio_path = _write_temp_audio(audio_bytes, filename, ".wav")
        command = [str(binary), "-m", str(model_path), "-a", str(audio_path)]
        if vad_path and vad_path.exists():
            command.extend(["--vad", str(vad_path), "--vad-maxseg", str(self.settings.sensevoice_max_segment_ms)])

        try:
            result = subprocess.run(
                command,
                cwd=str(self.settings.sensevoice_engine_dir),
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=self.settings.sensevoice_timeout_seconds,
                check=False,
            )
            if result.returncode != 0:
                message = result.stderr.strip() or result.stdout.strip() or f"exit code {result.returncode}"
                raise RuntimeError(message)
            return _clean_sensevoice_output(result.stdout)
        finally:
            audio_path.unlink(missing_ok=True)

    def _transcribe_with_funasr(
        self,
        *,
        audio_bytes: bytes,
        filename: str | None,
        dialect: str,
    ) -> str:
        self._load_fun_asr()
        assert self._model is not None
        assert self._postprocess is not None

        audio_path = _write_temp_audio(audio_bytes, filename, ".webm")
        try:
            result = self._model.generate(
                input=str(audio_path),
                cache={},
                language=DIALECT_TO_SENSEVOICE_LANGUAGE.get(dialect, "auto"),
                use_itn=True,
                batch_size_s=60,
                merge_vad=True,
                merge_length_s=15,
            )
            raw_text = result[0].get("text", "") if result else ""
            return str(self._postprocess(raw_text))
        finally:
            audio_path.unlink(missing_ok=True)


class CosyVoiceAdapter:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._model: Any | None = None
        self._torchaudio: Any | None = None

    @property
    def ready(self) -> bool:
        return self._model is not None

    def _load(self) -> None:
        if self._model is not None:
            return

        model_dir = Path(self.settings.cosyvoice_model_dir)
        if not model_dir.exists():
            raise RuntimeError(f"CosyVoice model dir not found: {model_dir}")

        if self.settings.cosyvoice_repo:
            repo_path = Path(self.settings.cosyvoice_repo).resolve()
            if not repo_path.exists():
                raise RuntimeError(f"CosyVoice repo not found: {repo_path}")
            matcha_path = repo_path / "third_party" / "Matcha-TTS"
            if not (matcha_path / "matcha").exists():
                raise RuntimeError(
                    "CosyVoice Matcha-TTS submodule not found. Put the Matcha-TTS "
                    f"repo contents under {matcha_path} or clone CosyVoice with --recursive."
                )
            for path in (repo_path, matcha_path):
                path_text = str(path)
                if path_text not in sys.path:
                    sys.path.insert(0, path_text)
            if find_spec("pkg_resources") is None:
                raise RuntimeError(
                    "CosyVoice dependency pkg_resources not found. The current "
                    "setuptools version may be too new; install a setuptools release "
                    "that still provides pkg_resources, for example setuptools==80.9.0."
                )

        from cosyvoice.cli.cosyvoice import AutoModel
        import torchaudio

        self._model = AutoModel(model_dir=str(model_dir))
        self._torchaudio = torchaudio

    def synthesize_zero_shot(
        self,
        *,
        target_text: str,
        prompt_text: str,
        speaker_audio: bytes,
        filename: str | None,
    ) -> str | None:
        if not speaker_audio:
            return None

        self._load()
        assert self._model is not None
        assert self._torchaudio is not None

        self.settings.generated_audio_dir.mkdir(parents=True, exist_ok=True)
        runtime_audio_dir = Path(self.settings.cosyvoice_audio_dir)
        prompt_dir = runtime_audio_dir / "prompt"
        output_dir = runtime_audio_dir / "generated"
        output_dir.mkdir(parents=True, exist_ok=True)

        output_name = f"clone_{uuid.uuid4().hex}.wav"
        prompt_path = _write_temp_audio(speaker_audio, filename, ".wav", directory=prompt_dir)
        work_output_path = output_dir / output_name
        public_output_path = self.settings.generated_audio_dir / output_name
        inference_prompt_text = (
            _format_cosyvoice3_prompt(prompt_text)
            if (Path(self.settings.cosyvoice_model_dir) / "cosyvoice3.yaml").exists()
            else prompt_text
        )

        try:
            for _, chunk in enumerate(
                self._model.inference_zero_shot(
                    target_text,
                    inference_prompt_text,
                    str(prompt_path),
                    stream=False,
                )
            ):
                self._torchaudio.save(
                    str(work_output_path),
                    chunk["tts_speech"],
                    self._model.sample_rate,
                )
                break
            if not work_output_path.exists():
                raise RuntimeError("CosyVoice did not return generated audio.")
            shutil.copyfile(work_output_path, public_output_path)
        finally:
            prompt_path.unlink(missing_ok=True)
            work_output_path.unlink(missing_ok=True)

        return f"/static/generated/{public_output_path.name}"

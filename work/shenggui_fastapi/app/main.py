from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, File, Form, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from starlette.concurrency import run_in_threadpool

from .settings import STATIC_DIR, settings
from .services.speech import DIALECT_LIBRARY, SpeechAssessmentService, VoiceCloneService


BASE_DIR = Path(__file__).resolve().parent
PROJECT_DIR = BASE_DIR.parent

app = FastAPI(
    title="声归 Shenggui API",
    description="Dialect learning MVP API for SenseVoice-Small assessment and CosyVoice 3.0 voice cloning.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

assessment_service = SpeechAssessmentService()
voice_clone_service = VoiceCloneService()


@app.get("/", include_in_schema=False)
def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/api/health")
def health() -> dict[str, object]:
    cosy_repo = Path(settings.cosyvoice_repo) if settings.cosyvoice_repo else None
    matcha_dir = cosy_repo / "third_party" / "Matcha-TTS" if cosy_repo else None
    return {
        "ok": True,
        "backend": settings.model_backend,
        "models": {
            "assessment": {
                "name": assessment_service.model_name,
                "ready": assessment_service.model_ready,
                "runtime": settings.sensevoice_runtime,
                "engine": str(settings.sensevoice_binary),
                "gguf_model": str(settings.sensevoice_gguf_model_path or ""),
                "vad_model": str(settings.sensevoice_vad_gguf_path or ""),
            },
            "voice_clone": {
                "name": voice_clone_service.model_name,
                "ready": voice_clone_service.model_ready,
                "repo": settings.cosyvoice_repo,
                "model_dir": settings.cosyvoice_model_dir,
                "matcha_tts": str(matcha_dir or ""),
                "matcha_ready": bool(matcha_dir and (matcha_dir / "matcha").exists()),
            },
            "live2d": "disabled",
        },
    }


@app.get("/api/lessons")
def lessons() -> dict[str, object]:
    return {"dialects": DIALECT_LIBRARY}


@app.post("/api/evaluate")
async def evaluate(
    dialect: str = Form("yue"),
    scene: str = Form("market"),
    stage: str = Form("discover"),
    audio: UploadFile | None = File(None),
) -> dict[str, object]:
    audio_bytes = await audio.read() if audio else b""
    return await run_in_threadpool(
        assessment_service.evaluate,
        dialect=dialect,
        scene=scene,
        stage=stage,
        audio_bytes=audio_bytes,
        filename=audio.filename if audio else None,
    )


@app.post("/api/clone-preview")
async def clone_preview(
    dialect: str = Form("yue"),
    scene: str = Form("market"),
    prompt_text: str | None = Form(None),
    speaker_audio: UploadFile | None = File(None),
) -> dict[str, object]:
    speaker_bytes = await speaker_audio.read() if speaker_audio else b""
    return await run_in_threadpool(
        voice_clone_service.create_preview,
        dialect=dialect,
        scene=scene,
        speaker_audio=speaker_bytes,
        filename=speaker_audio.filename if speaker_audio else None,
        prompt_text=prompt_text,
    )

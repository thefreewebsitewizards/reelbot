import threading
from pathlib import Path
from loguru import logger

from src.config import settings
from src.models import TranscriptResult

# Lazy-load the model to avoid slow startup
_model = None
_model_lock = threading.Lock()

# Whisper is CPU-bound — limit concurrent transcriptions to 2 (matches VPS core count)
_transcribe_semaphore = threading.Semaphore(2)


def _get_model():
    global _model
    if _model is None:
        with _model_lock:
            if _model is None:
                from faster_whisper import WhisperModel
                logger.info(f"Loading Whisper model: {settings.whisper_model} ({settings.whisper_compute_type})")
                _model = WhisperModel(
                    settings.whisper_model,
                    device=settings.whisper_device,
                    compute_type=settings.whisper_compute_type,
                )
    return _model


def transcribe(audio_path: Path) -> TranscriptResult:
    """Transcribe audio file using faster-whisper.

    Uses a semaphore to limit concurrent transcriptions to 2 (CPU-bound).
    Other pipeline steps (download, LLM calls) run without this gate.
    """
    logger.info(f"Transcribing {audio_path}")

    with _transcribe_semaphore:
        model = _get_model()
        segments, info = model.transcribe(str(audio_path), beam_size=5)

        text_parts = []
        for segment in segments:
            text_parts.append(segment.text.strip())

    full_text = " ".join(text_parts)
    logger.info(f"Transcribed {info.duration:.1f}s of {info.language} audio ({len(full_text)} chars)")

    return TranscriptResult(
        text=full_text,
        language=info.language,
        duration=info.duration,
    )

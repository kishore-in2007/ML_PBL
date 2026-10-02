from __future__ import annotations

import re
import subprocess
import sys
import tempfile
import uuid
import wave
from dataclasses import asdict, dataclass
from functools import lru_cache
from pathlib import Path

from app.config import settings


@dataclass
class VoiceCommand:
    intent: str
    action: str
    route: str | None
    label: str
    params: dict
    requires_confirmation: bool = False

    def to_dict(self) -> dict:
        return asdict(self)


COMMAND_CAPABILITIES = [
    {
        "intent": "wound_status",
        "examples": ["show wound status", "how is my wound healing", "latest analysis"],
        "route": "/patient/analysis-result",
    },
    {
        "intent": "upload_wound_photo",
        "examples": ["upload wound photo", "open camera", "capture wound"],
        "route": "/patient/capture",
    },
    {
        "intent": "recovery_trends",
        "examples": ["show recovery trends", "healing progress", "open trends"],
        "route": "/patient/trends",
    },
    {
        "intent": "reminders",
        "examples": ["show reminders", "medicine reminder", "remind me at 8 pm"],
        "route": "/patient/reminders",
    },
    {
        "intent": "care_team",
        "examples": ["contact doctor", "show care team", "clinic details"],
        "route": "/patient/care-team",
    },
    {
        "intent": "share_report",
        "examples": ["share report with doctor", "send recovery report"],
        "route": "/patient/care-team",
    },
    {
        "intent": "profile",
        "examples": ["open profile", "my surgery details"],
        "route": "/patient/profile",
    },
    {
        "intent": "emergency_guidance",
        "examples": ["I have fever and severe pain", "bleeding emergency", "pus smell"],
        "route": "/patient/care-team",
    },
]


def normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip())


def _contains(text: str, *terms: str) -> bool:
    return any(term in text for term in terms)


def _extract_time(text: str) -> tuple[str, str] | None:
    match = re.search(r"\b(?:at|by|around)\s+(\d{1,2})(?::(\d{2}))?\s*(am|pm)?\b", text)
    if not match:
        return None
    hour = int(match.group(1))
    minute = int(match.group(2) or 0)
    suffix = match.group(3)
    if suffix == "pm" and hour < 12:
        hour += 12
    if suffix == "am" and hour == 12:
        hour = 0
    if hour > 23 or minute > 59:
        return None
    value = f"{hour:02d}:{minute:02d}"
    label_hour = hour % 12 or 12
    label_suffix = "AM" if hour < 12 else "PM"
    return value, f"Daily at {label_hour}:{minute:02d} {label_suffix}"


def parse_patient_command(message: str) -> VoiceCommand:
    original = normalize_text(message)
    text = original.lower()

    urgent_terms = [
        "emergency",
        "severe pain",
        "bleeding",
        "fever",
        "pus",
        "bad smell",
        "smell",
        "redness spreading",
        "swelling",
        "infection",
    ]
    if _contains(text, *urgent_terms):
        return VoiceCommand(
            intent="emergency_guidance",
            action="escalate_triage",
            route="/patient/care-team",
            label="Create urgent care alert",
            params={"symptom_text": original},
            requires_confirmation=False,
        )

    if _contains(text, "upload", "capture", "camera", "photo", "picture", "image"):
        return VoiceCommand(
            intent="upload_wound_photo",
            action="navigate",
            route="/patient/capture",
            label="Open daily wound photo capture",
            params={"requires_file": True},
        )

    if _contains(text, "trend", "progress", "graph", "healing history", "recovery"):
        return VoiceCommand(
            intent="recovery_trends",
            action="read_recovery_overview",
            route="/patient/trends",
            label="Open recovery trends",
            params={},
        )

    if _contains(text, "remind me", "add reminder", "create reminder", "set reminder"):
        time_info = _extract_time(text) or ("08:00", "Daily at 8:00 AM")
        reminder_type = "medication" if _contains(text, "medicine", "medication", "tablet", "pill") else "care"
        title = "Medicine Reminder" if reminder_type == "medication" else "Care Reminder"
        return VoiceCommand(
            intent="create_reminder",
            action="create_reminder",
            route="/patient/reminders",
            label="Create reminder",
            params={
                "title": title,
                "reminder_type": reminder_type,
                "schedule_time": time_info[0],
                "schedule_label": time_info[1],
                "notes": original,
            },
        )

    if _contains(text, "reminder", "medicine", "medication", "dressing"):
        return VoiceCommand(
            intent="reminders",
            action="read_reminders",
            route="/patient/reminders",
            label="Open reminders",
            params={},
        )

    if _contains(text, "share report", "send report", "recovery report"):
        return VoiceCommand(
            intent="share_report",
            action="share_report",
            route="/patient/care-team",
            label="Share recovery report",
            params={"title": "Voice Requested Recovery Report"},
        )

    if _contains(text, "doctor", "care team", "contact", "clinic", "appointment", "call"):
        return VoiceCommand(
            intent="care_team",
            action="read_care_team",
            route="/patient/care-team",
            label="Open care team",
            params={},
        )

    if _contains(text, "profile", "surgery", "my details"):
        return VoiceCommand(
            intent="profile",
            action="read_profile",
            route="/patient/profile",
            label="Open profile",
            params={},
        )

    if _contains(text, "home", "dashboard"):
        return VoiceCommand(
            intent="dashboard",
            action="navigate",
            route="/patient/dashboard",
            label="Open dashboard",
            params={},
        )

    if _contains(text, "wound", "healing", "status", "analysis", "result", "pain"):
        return VoiceCommand(
            intent="wound_status",
            action="read_wound_status",
            route="/patient/analysis-result",
            label="Read latest wound status",
            params={},
        )

    return VoiceCommand(
        intent="general_help",
        action="help",
        route="/patient/voice-assistant",
        label="Voice assistant help",
        params={},
    )


@lru_cache(maxsize=1)
def _whisper_model():
    from faster_whisper import WhisperModel

    return WhisperModel(
        settings.WHISPER_MODEL_SIZE,
        device=settings.WHISPER_DEVICE,
        compute_type=settings.WHISPER_COMPUTE_TYPE,
    )


def transcribe_audio(audio_bytes: bytes, suffix: str = ".webm") -> str:
    suffix = suffix if suffix.startswith(".") else f".{suffix}"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_audio:
        temp_audio.write(audio_bytes)
        temp_path = Path(temp_audio.name)
    try:
        segments, _info = _whisper_model().transcribe(str(temp_path), beam_size=1)
        return normalize_text(" ".join(segment.text for segment in segments))
    finally:
        temp_path.unlink(missing_ok=True)


def _write_silence(path: Path, seconds: float = 0.2):
    framerate = 16000
    frames = int(seconds * framerate)
    with wave.open(str(path), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(framerate)
        wav.writeframes(b"\x00\x00" * frames)


def synthesize_speech(text: str, output_dir: str | Path = "uploads/voice") -> str | None:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    wav_path = output_path / f"voice-{uuid.uuid4().hex}.wav"

    if settings.PIPER_EXECUTABLE and settings.PIPER_MODEL_PATH:
        try:
            subprocess.run(
                [
                    settings.PIPER_EXECUTABLE,
                    "--model",
                    settings.PIPER_MODEL_PATH,
                    "--output_file",
                    str(wav_path),
                ],
                input=text,
                text=True,
                check=True,
                capture_output=True,
                timeout=30,
            )
            return str(wav_path)
        except Exception:
            wav_path.unlink(missing_ok=True)

    try:
        script = (
            "import sys, pyttsx3; "
            "engine=pyttsx3.init(); "
            "engine.save_to_file(sys.argv[1], sys.argv[2]); "
            "engine.runAndWait()"
        )
        subprocess.run(
            [sys.executable, "-c", script, text, str(wav_path)],
            check=True,
            capture_output=True,
            timeout=20,
        )
        if wav_path.exists() and wav_path.stat().st_size > 0:
            return str(wav_path)
    except Exception:
        wav_path.unlink(missing_ok=True)

    try:
        _write_silence(wav_path)
        return str(wav_path)
    except Exception:
        return None

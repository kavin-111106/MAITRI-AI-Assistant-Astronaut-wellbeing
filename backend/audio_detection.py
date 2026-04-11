from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
import logging

import librosa
import numpy as np
import soundfile as sf
from fastapi import HTTPException, UploadFile, status

logger = logging.getLogger("maitri.audio")


@dataclass
class _SignalProfile:
    duration_sec: float
    sample_rate_hz: int
    rms_mean: float
    zcr_mean: float
    spectral_centroid_hz: float
    spectral_rolloff_hz: float
    estimated_tempo_bpm: float
    estimated_pitch_hz: float
    estimated_speech_rate_wpm: float
    silence_ratio: float
    clipping_ratio: float


async def analyze_audio_upload(file: UploadFile, astronaut_id: int | None = None) -> dict:
    """
    End-to-end audio detection:
    - validates file
    - decodes waveform
    - extracts acoustic features
    - computes heuristic risk/stress classification
    """
    _validate_audio_file(file)

    raw_bytes = await file.read()
    if not raw_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded audio file is empty",
        )

    target_sr = 16000
    y, sr = _decode_audio(raw_bytes, target_sr=target_sr)
    signal = _extract_signal_profile(y=y, sr=sr)
    quality_flags = _quality_flags(signal)
    risk = _classify_risk(signal, quality_flags)

    logger.info(
        "Audio analyzed astronaut:%s file:%s duration:%.2fs risk:%s score:%.2f",
        astronaut_id,
        file.filename,
        signal.duration_sec,
        risk["severity"],
        risk["risk_score"],
    )

    return {
        "filename": file.filename,
        "content_type": file.content_type,
        "analysis": {
            "duration_sec": round(signal.duration_sec, 3),
            "sample_rate_hz": signal.sample_rate_hz,
            "rms_mean": round(signal.rms_mean, 6),
            "zcr_mean": round(signal.zcr_mean, 6),
            "spectral_centroid_hz": round(signal.spectral_centroid_hz, 2),
            "spectral_rolloff_hz": round(signal.spectral_rolloff_hz, 2),
            "estimated_tempo_bpm": round(signal.estimated_tempo_bpm, 2),
            "estimated_pitch_hz": round(signal.estimated_pitch_hz, 2),
            "estimated_speech_rate_wpm": round(signal.estimated_speech_rate_wpm, 2),
            "silence_ratio": round(signal.silence_ratio, 4),
            "clipping_ratio": round(signal.clipping_ratio, 4),
            "quality_flags": quality_flags,
        },
        "risk": risk,
        "notes": [
            "Heuristic analysis only; not a medical diagnosis.",
            "Use alongside text-chat health insights for mission decisions.",
        ],
    }


def _validate_audio_file(file: UploadFile) -> None:
    allowed = {
        "audio/wav",
        "audio/x-wav",
        "audio/mpeg",
        "audio/mp3",
        "audio/ogg",
        "audio/x-m4a",
        "audio/mp4",
        "audio/flac",
    }

    if file.content_type and file.content_type.lower() not in allowed:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Unsupported audio type: {file.content_type}",
        )


def _decode_audio(raw_bytes: bytes, target_sr: int = 16000) -> tuple[np.ndarray, int]:
    # Attempt flexible decoding first (supports many codecs when backend libs exist).
    try:
        y, sr = librosa.load(BytesIO(raw_bytes), sr=target_sr, mono=True)
        if y.size == 0:
            raise ValueError("Decoded empty audio")
        return y, sr
    except Exception:
        # Deterministic fallback (PCM-compatible containers).
        try:
            audio, sr = sf.read(BytesIO(raw_bytes), always_2d=False)
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to decode audio file. Provide a valid WAV/MP3/OGG/M4A file.",
            ) from exc

        if isinstance(audio, np.ndarray) and audio.ndim > 1:
            audio = np.mean(audio, axis=1)
        y = np.asarray(audio, dtype=np.float32)
        if y.size == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Audio has no samples after decoding",
            )
        if sr != target_sr:
            y = librosa.resample(y, orig_sr=sr, target_sr=target_sr)
            sr = target_sr
        return y, sr


def _extract_signal_profile(y: np.ndarray, sr: int) -> _SignalProfile:
    if y.size < sr:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Audio is too short. Provide at least 1 second.",
        )

    duration = float(y.shape[0] / sr)
    y_abs = np.abs(y)

    rms = librosa.feature.rms(y=y)[0]
    zcr = librosa.feature.zero_crossing_rate(y=y)[0]
    spectral_centroid = librosa.feature.spectral_centroid(y=y, sr=sr)[0]
    spectral_rolloff = librosa.feature.spectral_rolloff(y=y, sr=sr, roll_percent=0.85)[0]

    tempo = float(librosa.feature.tempo(y=y, sr=sr, aggregate=np.median)[0])

    f0 = librosa.yin(
        y=y,
        fmin=50,
        fmax=450,
        sr=sr,
        frame_length=2048,
        hop_length=512,
    )
    voiced_f0 = f0[np.isfinite(f0)]
    median_pitch = float(np.median(voiced_f0)) if voiced_f0.size else 0.0

    onsets = librosa.onset.onset_detect(y=y, sr=sr, units="time")
    speech_rate_wpm = float((len(onsets) / max(duration, 1e-6)) * 60.0)

    silence_ratio = float(np.mean(y_abs < 0.01))
    clipping_ratio = float(np.mean(y_abs >= 0.99))

    return _SignalProfile(
        duration_sec=duration,
        sample_rate_hz=int(sr),
        rms_mean=float(np.mean(rms)),
        zcr_mean=float(np.mean(zcr)),
        spectral_centroid_hz=float(np.mean(spectral_centroid)),
        spectral_rolloff_hz=float(np.mean(spectral_rolloff)),
        estimated_tempo_bpm=tempo,
        estimated_pitch_hz=median_pitch,
        estimated_speech_rate_wpm=speech_rate_wpm,
        silence_ratio=silence_ratio,
        clipping_ratio=clipping_ratio,
    )


def _quality_flags(signal: _SignalProfile) -> list[str]:
    flags: list[str] = []

    if signal.duration_sec < 3.0:
        flags.append("very_short_audio")
    if signal.rms_mean < 0.01:
        flags.append("very_low_volume")
    if signal.silence_ratio > 0.65:
        flags.append("mostly_silence")
    if signal.clipping_ratio > 0.01:
        flags.append("possible_clipping")

    return flags


def _classify_risk(signal: _SignalProfile, quality_flags: list[str]) -> dict:
    score = 0.0
    indicators: list[str] = []

    if signal.estimated_speech_rate_wpm > 195:
        score += 0.35
        indicators.append("elevated speaking rhythm")
    elif signal.estimated_speech_rate_wpm < 85:
        score += 0.25
        indicators.append("slowed speaking rhythm")

    if signal.zcr_mean > 0.12:
        score += 0.20
        indicators.append("high voice agitation signal")

    if signal.rms_mean > 0.16:
        score += 0.20
        indicators.append("raised vocal energy")
    elif signal.rms_mean < 0.015:
        score += 0.18
        indicators.append("reduced vocal energy")

    if signal.spectral_centroid_hz > 3000:
        score += 0.15
        indicators.append("high-frequency tension profile")

    if signal.silence_ratio > 0.55:
        score += 0.15
        indicators.append("frequent pauses")

    if "possible_clipping" in quality_flags:
        score += 0.05
    if "very_short_audio" in quality_flags:
        score = max(score - 0.10, 0.0)

    score = float(min(max(score, 0.0), 1.0))

    if score >= 0.8:
        severity = "critical"
        state = "high_arousal_distress"
        action = "Trigger immediate follow-up and request real-time voice check with mission psychologist."
    elif score >= 0.6:
        severity = "high"
        state = "stressed"
        action = "Schedule prompt check-in and correlate with recent text-chat health indicators."
    elif score >= 0.35:
        severity = "medium"
        state = "elevated_strain"
        action = "Monitor trend over next sessions; encourage rest and support protocols."
    elif score >= 0.18:
        severity = "low"
        state = "mild_variation"
        action = "No urgent action; continue routine monitoring."
    else:
        severity = "none"
        state = "calm"
        action = "No action required."

    if not indicators:
        indicators.append("no strong stress markers detected")

    return {
        "severity": severity,
        "state": state,
        "risk_score": round(score, 3),
        "confidence": round(_confidence_from_quality(quality_flags), 3),
        "indicators": indicators,
        "recommended_action": action,
    }


def _confidence_from_quality(quality_flags: list[str]) -> float:
    penalty = 0.0
    for flag in quality_flags:
        if flag in {"very_short_audio", "mostly_silence"}:
            penalty += 0.15
        elif flag in {"very_low_volume", "possible_clipping"}:
            penalty += 0.08
    return max(0.35, 0.95 - penalty)

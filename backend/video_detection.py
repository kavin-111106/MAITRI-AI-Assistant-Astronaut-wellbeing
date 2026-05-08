from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
import logging
import tempfile
import shutil
import os
import asyncio
from concurrent.futures import ThreadPoolExecutor
import time
import warnings

import cv2
import torch
import torch.nn as nn
from torchvision import models, transforms
from PIL import Image
import numpy as np
from fastapi import HTTPException, UploadFile, status
import subprocess


logger = logging.getLogger("maitri.video")


@dataclass
class _FaceDetection:
    bbox: dict
    primary_emotion: dict
    all_emotions: dict
    top_3: list


@dataclass
class _FrameResult:
    frame_number: int
    timestamp_seconds: float
    faces_detected: int
    detections: list[_FaceDetection]


@dataclass
class _VideoProfile:
    total_frames: int
    fps: float
    duration_seconds: float
    frames_processed: int
    sample_rate: int
    total_faces_detected: int
    dominant_emotion: str | None
    emotion_distribution: dict


# =========================
# FINAL ULTRA-AGGRESSIVE CONFIG
# =========================
_MAX_VIDEO_DURATION = 60
_MAX_FRAMES_TO_PROCESS = 10        # ONLY 10 frames max
_FACE_DETECTION_SCALE = 0.2        # 20% resolution for detection
_KEEP_ONLY_LARGEST_FACE = True     # Only analyze the largest face per frame
_BATCH_SIZE = 32                   # Maximum batching
_MAX_WORKERS = 4

_CLASS_NAMES = ["angry", "disgust", "fear", "happy", "neutral", "sad", "surprise"]
_IMG_SIZE = 224
_DEVICE = torch.device("cpu")

_TRANSFORM = transforms.Compose([
    transforms.Resize((_IMG_SIZE, _IMG_SIZE)),
    transforms.ToTensor(),
    transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])
])

# Face detector
_YUNET_MODEL = None
_FACE_CASCADE = None


def _get_face_detector():
    """Get the best available face detector without external files."""
    global _YUNET_MODEL, _FACE_CASCADE

    if _YUNET_MODEL is None and _FACE_CASCADE is None:
        try:
            # Try multiple paths for YuNet
            yunet_paths = [
                os.path.join(cv2.data.haarcascades, "..", "yunet", "face_detection_yunet_2023mar.onnx"),
                "/usr/share/opencv4/models/face_detection_yunet_2023mar.onnx",
                "/usr/local/share/opencv4/models/face_detection_yunet_2023mar.onnx",
                os.path.expanduser("~/.local/share/opencv4/models/face_detection_yunet_2023mar.onnx"),
            ]

            model_path = None
            for p in yunet_paths:
                if os.path.exists(p):
                    model_path = p
                    break

            if model_path:
                _YUNET_MODEL = cv2.FaceDetectorYN.create(
                    model=model_path,
                    config="",
                    input_size=(320, 320),
                    score_threshold=0.6,
                    nms_threshold=0.3,
                    top_k=10
                )
                logger.info("Using YuNet face detector")
            else:
                raise FileNotFoundError("YuNet model not found in any standard location")
        except Exception as e:
            logger.warning("YuNet not available (%s), using Haar Cascade", e)
            _FACE_CASCADE = cv2.CascadeClassifier(
                cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
            )
            _YUNET_MODEL = "haar"

    return _YUNET_MODEL


def _detect_faces_frame(frame: np.ndarray) -> list[tuple[int, int, int, int]]:
    """Detect faces. Returns list of (x, y, w, h)."""
    detector = _get_face_detector()
    h, w = frame.shape[:2]

    if detector == "haar":
        return _detect_faces_haar(frame)

    # YuNet path
    scale = _FACE_DETECTION_SCALE
    small = cv2.resize(frame, None, fx=scale, fy=scale)
    sh, sw = small.shape[:2]

    detector.setInputSize((sw, sh))
    _, faces = detector.detect(small)

    if faces is None:
        return []

    results = []
    for face in faces:
        x, y, fw, fh = face[:4]
        x1 = int(x / scale)
        y1 = int(y / scale)
        x2 = int((x + fw) / scale)
        y2 = int((y + fh) / scale)

        x1, y1 = max(0, x1), max(0, y1)
        x2, y2 = min(w, x2), min(h, y2)

        if x2 > x1 and y2 > y1 and (x2-x1) > 40 and (y2-y1) > 40:
            results.append((x1, y1, x2-x1, y2-y1))

    return results


def _detect_faces_haar(frame: np.ndarray) -> list[tuple[int, int, int, int]]:
    """Fallback Haar with aggressive speed settings."""
    h, w = frame.shape[:2]
    scale = _FACE_DETECTION_SCALE
    small = cv2.resize(frame, None, fx=scale, fy=scale)
    gray = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)

    faces = _FACE_CASCADE.detectMultiScale(
        gray, scaleFactor=1.3, minNeighbors=2, minSize=(30, 30)
    )

    results = []
    for (x, y, fw, fh) in faces:
        x1 = int(x / scale)
        y1 = int(y / scale)
        w1 = int(fw / scale)
        h1 = int(fh / scale)
        if w1 > 40 and h1 > 40:
            results.append((x1, y1, w1, h1))

    return results


# =========================
# MODEL — Pre-loaded at import time
# =========================
_MODEL = None
_MODEL_LOADED_AT = None

def _load_model_at_startup():
    """Call this once at application startup to pre-load the model."""
    global _MODEL, _MODEL_LOADED_AT
    if _MODEL is not None:
        return

    logger.info("Pre-loading emotion model at startup...")
    t0 = time.time()

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        model = models.resnet18(weights=None)

    num_ftrs = model.fc.in_features
    model.fc = nn.Sequential(nn.Dropout(0.5), nn.Linear(num_ftrs, len(_CLASS_NAMES)))

    model_paths = ["backend/model.pth", "video_emotion_model.pth", "emotion_model.pth"]
    loaded = False

    for path in model_paths:
        if os.path.exists(path):
            checkpoint = torch.load(path, map_location=_DEVICE)
            if isinstance(checkpoint, dict) and "model_state" in checkpoint:
                model.load_state_dict(checkpoint["model_state"])
            else:
                model.load_state_dict(checkpoint)
            loaded = True
            logger.info("Loaded model from %s", path)
            break

    if not loaded:
        logger.warning("No model found — using untrained weights")

    model = model.to(_DEVICE).eval()

    # TorchScript trace for faster CPU
    try:
        with torch.no_grad():
            example = torch.randn(_BATCH_SIZE, 3, _IMG_SIZE, _IMG_SIZE)
            traced = torch.jit.trace(model, example)
            model = traced
        logger.info("Model TorchScript traced (batch size %d)", _BATCH_SIZE)
    except Exception as e:
        logger.warning("TorchScript failed: %s", e)

    _MODEL = model
    _MODEL_LOADED_AT = time.time()
    logger.info("Model ready in %.2fs", _MODEL_LOADED_AT - t0)


def _get_model():
    if _MODEL is None:
        _load_model_at_startup()
    return _MODEL


async def analyze_video_upload(file: UploadFile, astronaut_id: int | None = None) -> dict:
    _validate_video_file(file)
    raw_bytes = await file.read()
    if not raw_bytes:
        raise HTTPException(status_code=400, detail="Uploaded video file is empty")

    result = await asyncio.to_thread(_analyze_blocking, raw_bytes, file.filename, file.content_type, astronaut_id)
    return result


def _analyze_blocking(raw_bytes: bytes, filename: str, content_type: str, astronaut_id: int | None) -> dict:
    temp_dir = tempfile.mkdtemp()
    temp_path = os.path.join(temp_dir, f"upload_{filename}")

    try:
        with open(temp_path, "wb") as f:
            f.write(raw_bytes)

        video_profile, frame_results = _process_video_optimized(temp_path)
        risk = _classify_risk(video_profile, frame_results)

    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)

    logger.info(
        "Video analyzed astronaut:%s file:%s duration:%.2fs risk:%s score:%.2f",
        astronaut_id, filename, video_profile.duration_seconds, risk["severity"], risk["risk_score"],
    )

    return {
        "filename": filename,
        "content_type": content_type,
        "analysis": {
            "duration_sec": round(video_profile.duration_seconds, 3),
            "fps": round(video_profile.fps, 2),
            "total_frames": video_profile.total_frames,
            "frames_processed": video_profile.frames_processed,
            "sample_rate": video_profile.sample_rate,
            "total_faces_detected": video_profile.total_faces_detected,
            "dominant_emotion": video_profile.dominant_emotion,
            "emotion_distribution": video_profile.emotion_distribution,
        },
        "frames": [
            {
                "frame_number": fr.frame_number,
                "timestamp_seconds": fr.timestamp_seconds,
                "faces_detected": fr.faces_detected,
                "detections": [
                    {
                        "bbox": d.bbox,
                        "primary_emotion": d.primary_emotion,
                        "all_emotions": d.all_emotions,
                        "top_3": d.top_3,
                    }
                    for d in fr.detections
                ],
            }
            for fr in frame_results
        ],
        "risk": risk,
        "notes": [
            "Heuristic facial emotion analysis only; not a medical diagnosis.",
            "Use alongside text-chat and audio health insights for mission decisions.",
        ],
    }


def _validate_video_file(file: UploadFile) -> None:

    if not file.content_type or file.content_type == "application/octet-stream":
        return   # ← trust the filename extension instead
    logger.info("Video file content type: %s", file.content_type)

    allowed = {
        "video/mp4", "video/x-matroska", "video/avi", "video/x-msvideo",
        "video/quicktime", "video/webm", "video/x-flv", "video/x-ms-wmv", "video/mov",
    }
    base_type = (file.content_type or "").lower().split(";")[0].strip()
    if base_type and base_type not in allowed:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Unsupported video type: {file.content_type}",
        )


def _decode_video(video_path: str) -> tuple[cv2.VideoCapture, int, float, int]:
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to decode video file.",
        )
    
    fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    
    # Check if OpenCV can read the file properly
    if fps <= 0 or total_frames <= 0 or total_frames > 1000000000:
        # OpenCV can't read this WebM file - convert to MP4 with FFmpeg
        cap.release()
        
        converted_path = video_path.replace('.webm', '_converted.mp4')
        try:
            # Convert WebM to MP4 using FFmpeg
            result = subprocess.run([
                'ffmpeg', '-y', '-i', video_path,
                '-c:v', 'libx264', '-preset', 'fast',
                '-crf', '23', '-pix_fmt', 'yuv420p',
                '-movflags', '+faststart',
                '-f', 'mp4', converted_path
            ], capture_output=True, text=True, timeout=30)
            
            if result.returncode != 0:
                logger.error("FFmpeg conversion failed: %s", result.stderr)
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Video conversion failed: {result.stderr[:200]}"
                )
            
            # Try opening the converted file
            cap = cv2.VideoCapture(converted_path)
            if not cap.isOpened():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Failed to open converted video."
                )
            
            fps = cap.get(cv2.CAP_PROP_FPS)
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            
            # Clean up converted file after we're done
            # (handled in _analyze_blocking)
            
        except FileNotFoundError:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="FFmpeg not installed. Cannot process WebM files."
            )
        except subprocess.TimeoutExpired:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Video conversion timed out."
            )
    
    duration = total_frames / fps if fps > 0 else 0
    return cap, total_frames, fps, duration



def _detect_faces_batch(frames: list[np.ndarray]) -> list[list[tuple[int, int, int, int]]]:
    """Parallel face detection."""
    with ThreadPoolExecutor(max_workers=_MAX_WORKERS) as executor:
        results = list(executor.map(_detect_faces_frame, frames))
    return results


def _run_emotion_batch(faces: list[np.ndarray], model) -> list[tuple[int, float, dict, list]]:
    """Batched emotion inference."""
    if not faces:
        return []

    tensors = []
    for face in faces:
        rgb = cv2.cvtColor(face, cv2.COLOR_BGR2RGB)
        pil_img = Image.fromarray(rgb)
        tensor = _TRANSFORM(pil_img)
        tensors.append(tensor)

    batch_tensor = torch.stack(tensors).to(_DEVICE)

    with torch.no_grad():
        outputs = model(batch_tensor)
        probs = torch.softmax(outputs, dim=1)
        confidences, preds = torch.max(probs, dim=1)
        top3_probs, top3_indices = torch.topk(probs, k=3, dim=1)

    results = []
    for i in range(len(faces)):
        pred = preds[i].item()
        conf = confidences[i].item()
        all_emotions = {_CLASS_NAMES[j]: probs[i][j].item() for j in range(len(_CLASS_NAMES))}
        top3 = [
            {"label": _CLASS_NAMES[idx], "confidence": round(prob.item(), 4)}
            for idx, prob in zip(top3_indices[i], top3_probs[i])
        ]
        results.append((pred, conf, all_emotions, top3))

    return results


def _process_video_optimized(video_path: str) -> tuple[_VideoProfile, list[_FrameResult]]:
    """Ultra-fast video processing with grab/retrieve optimization."""
    cap, total_frames, fps, duration = _decode_video(video_path)

    if duration > _MAX_VIDEO_DURATION:
        cap.release()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Video too long ({duration:.1f}s). Max: {_MAX_VIDEO_DURATION}s."
        )

    # Calculate sample rate for exactly MAX_FRAMES
    sample_rate = max(1, int(total_frames / _MAX_FRAMES_TO_PROCESS))

    # For short videos, ensure we spread frames evenly
    if duration > 0 and duration < 5.0:
        sample_rate = max(1, int(fps / 2))

    logger.info(
        "Video: %.1fs, %d frames, %.1f fps → Sample rate: %d (max %d frames)",
        duration, total_frames, fps, sample_rate, _MAX_FRAMES_TO_PROCESS
    )

    # ═══════════════════════════════════════════════════════════════
    # OPTIMIZED FRAME EXTRACTION: grab() + retrieve()
    # grab() quickly skips frames without decoding pixels
    # retrieve() only decodes the frames we actually need
    # This cuts frame extraction time from ~17s to ~1-2s
    # ═══════════════════════════════════════════════════════════════
    frames_to_process = []
    frame_metadata = []
    frame_count = 0
    extracted_count = 0

    t0_extraction = time.time()

    while True:
        # Fast skip — doesn't decode pixels, just advances file pointer
        ret = cap.grab()
        if not ret:
            break

        # Only decode frames we actually want to analyze
        if frame_count % sample_rate == 0:
            ret, frame = cap.retrieve()
            if ret and frame is not None:
                timestamp = frame_count / fps if fps > 0 else 0
                frames_to_process.append(frame)
                frame_metadata.append((frame_count, timestamp))
                extracted_count += 1

                # Early exit if we have enough frames
                if extracted_count >= _MAX_FRAMES_TO_PROCESS:
                    break

        frame_count += 1

    cap.release()

    extraction_time = time.time() - t0_extraction
    logger.info("Frame extraction: %.2fs (%d frames decoded out of %d total)", 
                extraction_time, extracted_count, frame_count)

    if not frames_to_process:
        return _empty_profile(total_frames, fps, duration, sample_rate), []

    # PHASE 1: Face detection (parallel)
    logger.info("Detecting faces in %d frames...", len(frames_to_process))
    t0 = time.time()
    all_face_detections = _detect_faces_batch(frames_to_process)
    face_time = time.time() - t0
    logger.info("Face detection: %.2fs (%.1f ms/frame)", face_time, (face_time/len(frames_to_process))*1000)

    # PHASE 2: Select faces & infer emotions
    faces_for_inference = []
    face_location_map = []

    for frame_idx, detections in enumerate(all_face_detections):
        if not detections:
            continue

        if _KEEP_ONLY_LARGEST_FACE:
            # Keep only the largest face by area
            largest = max(detections, key=lambda d: d[2] * d[3])
            detections = [largest]

        for (x, y, w, h) in detections:
            face = frames_to_process[frame_idx][y:y+h, x:x+w]
            if face.size == 0 or w < 30 or h < 30:
                continue
            faces_for_inference.append(face)
            face_location_map.append((frame_idx, x, y, w, h))

    logger.info("Analyzing %d faces across %d frames", len(faces_for_inference), len(frames_to_process))

    model = _get_model()
    all_emotion_results = []

    if faces_for_inference:
        t0 = time.time()
        for i in range(0, len(faces_for_inference), _BATCH_SIZE):
            batch = faces_for_inference[i:i + _BATCH_SIZE]
            batch_results = _run_emotion_batch(batch, model)
            all_emotion_results.extend(batch_results)
        emotion_time = time.time() - t0
        logger.info("Emotion inference: %.2fs (%.1f ms/face)", 
                    emotion_time, (emotion_time/len(faces_for_inference))*1000)

    # PHASE 3: Build results
    frame_detections_map = {}
    all_emotions = []

    for i, (frame_idx, x, y, w, h) in enumerate(face_location_map):
        pred, conf, all_emotions_dict, top3 = all_emotion_results[i]

        detection = _FaceDetection(
            bbox={"x": int(x), "y": int(y), "width": int(w), "height": int(h)},
            primary_emotion={
                "label": _CLASS_NAMES[pred],
                "confidence": round(conf, 4)
            },
            all_emotions={k: round(v, 4) for k, v in all_emotions_dict.items()},
            top_3=top3
        )

        if frame_idx not in frame_detections_map:
            frame_detections_map[frame_idx] = []
        frame_detections_map[frame_idx].append(detection)
        all_emotions.append(_CLASS_NAMES[pred])

    frame_results = []
    for frame_idx, (frame_number, timestamp) in enumerate(frame_metadata):
        if frame_idx in frame_detections_map:
            detections = frame_detections_map[frame_idx]
            frame_results.append(_FrameResult(
                frame_number=frame_number,
                timestamp_seconds=round(timestamp, 2),
                faces_detected=len(detections),
                detections=detections
            ))

    emotion_distribution = {}
    for emotion in _CLASS_NAMES:
        count = all_emotions.count(emotion)
        emotion_distribution[emotion] = {
            "count": count,
            "percentage": round(count / len(all_emotions) * 100, 2) if all_emotions else 0
        }

    dominant = max(set(all_emotions), key=all_emotions.count) if all_emotions else None

    profile = _VideoProfile(
        total_frames=total_frames,
        fps=round(fps, 2),
        duration_seconds=round(duration, 2),
        frames_processed=len(frame_results),
        sample_rate=sample_rate,
        total_faces_detected=len(all_emotions),
        dominant_emotion=dominant,
        emotion_distribution=emotion_distribution
    )

    return profile, frame_results


def _empty_profile(total_frames: int, fps: float, duration: float, sample_rate: int) -> _VideoProfile:
    return _VideoProfile(
        total_frames=total_frames,
        fps=round(fps, 2),
        duration_seconds=round(duration, 2),
        frames_processed=0,
        sample_rate=sample_rate,
        total_faces_detected=0,
        dominant_emotion=None,
        emotion_distribution={e: {"count": 0, "percentage": 0} for e in _CLASS_NAMES}
    )


def _classify_risk(profile: _VideoProfile, frame_results: list[_FrameResult]) -> dict:
    score = 0.0
    indicators: list[str] = []

    if profile.total_faces_detected == 0:
        return {
            "severity": "unknown",
            "state": "no_face_detected",
            "risk_score": 0.0,
            "confidence": 0.0,
            "indicators": ["No faces detected in video"],
            "recommended_action": "Ensure face is visible and well-lit. Retry with front-facing camera.",
        }

    dist = profile.emotion_distribution
    angry_pct = dist.get("angry", {}).get("percentage", 0)
    fear_pct = dist.get("fear", {}).get("percentage", 0)
    sad_pct = dist.get("sad", {}).get("percentage", 0)
    disgust_pct = dist.get("disgust", {}).get("percentage", 0)
    happy_pct = dist.get("happy", {}).get("percentage", 0)
    neutral_pct = dist.get("neutral", {}).get("percentage", 0)

    if angry_pct > 30:
        score += 0.40
        indicators.append("sustained anger expression")
    elif angry_pct > 15:
        score += 0.25
        indicators.append("intermittent anger markers")

    if fear_pct > 25:
        score += 0.35
        indicators.append("fear/anxiety signals")
    elif fear_pct > 10:
        score += 0.20
        indicators.append("mild fear indicators")

    if sad_pct > 30:
        score += 0.30
        indicators.append("prolonged sadness")
    elif sad_pct > 15:
        score += 0.15
        indicators.append("sadness markers present")

    if disgust_pct > 15:
        score += 0.20
        indicators.append("disgust/aversion detected")

    if happy_pct > 50:
        score = max(score - 0.20, 0.0)
        indicators.append("strong positive affect")
    elif happy_pct > 25:
        score = max(score - 0.10, 0.0)
        indicators.append("moderate positive affect")

    if neutral_pct > 70:
        score = max(score - 0.05, 0.0)

    if len(frame_results) > 1:
        emotion_sequence = []
        for fr in frame_results:
            for det in fr.detections:
                emotion_sequence.append(det.primary_emotion["label"])

        if len(emotion_sequence) >= 3:
            shifts = sum(1 for i in range(1, len(emotion_sequence)) 
                        if emotion_sequence[i] != emotion_sequence[i-1])
            shift_ratio = shifts / (len(emotion_sequence) - 1)
            if shift_ratio > 0.6:
                score += 0.15
                indicators.append("unstable emotional state")

    low_conf_frames = sum(
        1 for fr in frame_results 
        for det in fr.detections 
        if det.primary_emotion["confidence"] < 0.5
    )
    if profile.total_faces_detected > 0 and low_conf_frames / profile.total_faces_detected > 0.3:
        score += 0.05
        indicators.append("uncertain detections")

    if profile.duration_seconds < 2.0:
        score = max(score - 0.10, 0.0)

    score = float(min(max(score, 0.0), 1.0))

    if score >= 0.8:
        severity, state, action = "critical", "high_arousal_distress", "Trigger immediate follow-up and request real-time video check with mission psychologist."
    elif score >= 0.6:
        severity, state, action = "high", "stressed", "Schedule prompt check-in and correlate with recent text-chat and audio health indicators."
    elif score >= 0.35:
        severity, state, action = "medium", "elevated_strain", "Monitor trend over next sessions; encourage rest and support protocols."
    elif score >= 0.18:
        severity, state, action = "low", "mild_variation", "No urgent action; continue routine monitoring."
    else:
        severity, state, action = "none", "calm", "No action required."

    if not indicators:
        indicators.append("no strong stress markers detected")

    return {
        "severity": severity,
        "state": state,
        "risk_score": round(score, 3),
        "confidence": round(_confidence_from_profile(profile), 3),
        "indicators": indicators,
        "recommended_action": action,
    }


def _confidence_from_profile(profile: _VideoProfile) -> float:
    penalty = 0.0
    if profile.duration_seconds < 3.0:
        penalty += 0.15
    if profile.total_faces_detected == 0:
        penalty += 0.30
    elif profile.total_faces_detected < 5:
        penalty += 0.10
    if profile.frames_processed < 3:
        penalty += 0.15
    return max(0.40, 0.95 - penalty)
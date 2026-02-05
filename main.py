from fastapi import FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
import base64, io
import logging
import numpy as np
import soundfile as sf
import librosa
import os

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

app = FastAPI(title="VoiceGuard API")


@app.on_event("startup")
def startup():
    log.info("VoiceGuard server started. Open in browser: http://127.0.0.1:8000")


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

API_KEY = "team_hcl_2026_key"

# We only detect these two languages. Map any Whisper code to display name.
DISPLAY_EN = "English"
DISPLAY_HI = "Hindi (Devanagari)"


def lang_code_to_display(lang_code: str) -> str:
    """Map Whisper language code to English or Hindi (Devanagari). We support only these two."""
    if not lang_code:
        return DISPLAY_EN  # default to English if empty
    code = lang_code.lower().strip()
    # Hindi and common variants
    if code == "hi" or code.startswith("hi-") or code == "hin":
        return DISPLAY_HI
    # English and common variants
    if code == "en" or code.startswith("en-") or code == "eng":
        return DISPLAY_EN
    # Any other code: still show one of the two so UI is never "Unknown"
    return DISPLAY_EN


_whisper_model = None


def get_whisper_model():
    global _whisper_model
    if _whisper_model is None:
        import whisper
        # "base" is more accurate for Hindi than "tiny"
        _whisper_model = whisper.load_model("base")
    return _whisper_model


def detect_language_whisper(audio_mono: np.ndarray, sr: int) -> str:
    """Detect if audio is Hindi or English. We support only English and Hindi (Devanagari)."""
    import whisper
    try:
        # Whisper expects float32, 16 kHz
        if audio_mono.dtype != np.float32:
            if np.issubdtype(audio_mono.dtype, np.integer):
                audio_mono = audio_mono.astype(np.float32) / max(1, np.iinfo(audio_mono.dtype).max)
            else:
                audio_mono = audio_mono.astype(np.float32)
        if sr != 16000:
            audio_mono = librosa.resample(audio_mono, orig_sr=sr, target_sr=16000)
        # Whisper expects 30 seconds of audio for reliable language detection; pad_or_trim to 30s
        audio_mono = whisper.pad_or_trim(audio_mono)
        audio_mono = np.ascontiguousarray(audio_mono)
        model = get_whisper_model()
        result = model.transcribe(audio_mono, fp16=False, language=None)
        lang_code = (result.get("language") or "").strip()
        if not lang_code and result.get("segments"):
            lang_code = (result["segments"][0].get("language") or "").strip()
        log.info("Whisper detected language code: %r (raw result['language']: %r)", lang_code, result.get("language"))
        return lang_code_to_display(lang_code)
    except Exception as e:
        log.exception("Language detection failed, defaulting to English: %s", e)
        return DISPLAY_EN


def _load_ai_voice_model():
    """Load trained classifier and scaler only if trained on REAL data (not synthetic)."""
    try:
        import joblib
        from pathlib import Path
        models_dir = Path(__file__).resolve().parent / "models"
        flag_path = models_dir / "trained_on_real_data.flag"
        model_path = models_dir / "ai_voice_model.joblib"
        scaler_path = models_dir / "ai_voice_scaler.joblib"
        if flag_path.is_file() and model_path.is_file() and scaler_path.is_file():
            return joblib.load(model_path), joblib.load(scaler_path)
    except Exception as e:
        log.warning("Could not load trained AI voice model: %s", e)
    return None, None


_ai_voice_model = None
_ai_voice_scaler = None


def _get_ai_voice_model():
    global _ai_voice_model, _ai_voice_scaler
    if _ai_voice_model is None:
        _ai_voice_model, _ai_voice_scaler = _load_ai_voice_model()
    return _ai_voice_model, _ai_voice_scaler


def _heuristic_ai_vs_human(audio: np.ndarray, sr: int):
    """
    Research-based heuristic for real speech: human voice usually has more
    variation in energy and ZCR, and more spectral noise (breath); TTS is often
    more uniform and tonal. Returns (prediction, confidence 0-1).
    """
    if audio.ndim > 1:
        audio = np.mean(audio, axis=1)
    hop = 512
    frame_len = 2048
    rms = librosa.feature.rms(y=audio, frame_length=frame_len, hop_length=hop)[0]
    zcr = librosa.feature.zero_crossing_rate(audio, frame_length=frame_len, hop_length=hop)[0]
    rms = rms[rms > 0.001]
    if len(rms) < 5:
        return "HUMAN", 0.5
    # Coefficient of variation: human speech usually has higher variation
    rms_cv = np.std(rms) / (np.mean(rms) + 1e-8)
    zcr_std = np.std(zcr)
    rms_score = min(1.0, rms_cv / 1.2)
    zcr_score = min(1.0, zcr_std / 0.08)
    # Spectral flatness: human often noisier (higher); TTS more tonal (lower)
    try:
        flatness = librosa.feature.spectral_flatness(y=audio, hop_length=hop)[0]
        flatness = flatness[flatness > 1e-8]
        flat_mean = float(np.mean(flatness)) if len(flatness) else 0.01
        flat_score = min(1.0, flat_mean / 0.15)
    except Exception:
        flat_score = 0.5
    human_likeness = 0.45 * rms_score + 0.35 * zcr_score + 0.2 * flat_score
    human_likeness = max(0.0, min(1.0, human_likeness))
    confidence = 0.5 + 0.5 * abs(human_likeness - 0.5) * 2
    if human_likeness >= 0.42:
        return "HUMAN", float(confidence)
    return "AI_GENERATED", float(confidence)


def predict_ai_vs_human(audio: np.ndarray, sr: int):
    """
    Predict AI_GENERATED vs HUMAN. Uses model only if trained on real data;
    otherwise uses research-based heuristic for real speech.
    """
    model, scaler = _get_ai_voice_model()
    if model is not None and scaler is not None:
        try:
            from audio_features import extract_features
            feat = extract_features(audio, sr)
            feat = feat.reshape(1, -1)
            X = scaler.transform(feat)
            pred = model.predict(X)[0]
            proba = model.predict_proba(X)[0]
            confidence = float(proba[pred])
            label = "AI_GENERATED" if pred == 1 else "HUMAN"
            return label, confidence
        except Exception as e:
            log.warning("Trained model prediction failed, using heuristic: %s", e)
    return _heuristic_ai_vs_human(audio, sr)


def continuity_confidence(audio: np.ndarray, sr: int, top_db: int = 25) -> float:
    """
    Confidence based on speech continuity: less gaps/silence = higher confidence.
    Returns 0–1: ratio of time that is speech (non-silent) vs total.
    """
    if audio.size == 0:
        return 0.0
    if audio.ndim > 1:
        audio = np.mean(audio, axis=1)
    # Split into non-silent intervals
    intervals = librosa.effects.split(audio, top_db=top_db, ref=np.max)
    if len(intervals) == 0:
        return 0.0
    speech_samples = sum(end - start for start, end in intervals)
    total_samples = len(audio)
    return float(speech_samples) / float(total_samples)


class VoiceRequest(BaseModel):
    language: str
    audio_format: str
    audio_base64: str


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.post("/api/detect-voice")
def detect_voice(
    data: VoiceRequest,
    x_api_key: str = Header(..., alias="x-api-key")
):
    if x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API Key")

    try:
        audio_bytes = base64.b64decode(data.audio_base64)
        audio, sr = sf.read(io.BytesIO(audio_bytes))
    except Exception as e:
        raise HTTPException(status_code=400, detail="Invalid audio: " + str(e))

    # Mono for analysis
    if audio.ndim > 1:
        audio_mono = np.mean(audio, axis=1)
    else:
        audio_mono = audio

    # 1) Detected language: Hindi (Devanagari) or English
    language = detect_language_whisper(audio_mono, sr)

    # 2) Confidence from continuity: lacking in middle / gaps = low, continuous speech = high
    confidence = continuity_confidence(audio_mono, sr)
    confidence = round(min(1.0, max(0.0, confidence)), 2)

    # 3) AI vs Human: trained model if available, else heuristic
    prediction, _ = predict_ai_vs_human(audio, sr)

<<<<<<< HEAD
    return {
        "language": language,
        "prediction": prediction,
        "confidence": confidence
    }


# Serve frontend (after API routes so /api/* is matched first)
STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")
if os.path.isdir(STATIC_DIR):
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

    @app.get("/")
    def serve_app():
        return FileResponse(os.path.join(STATIC_DIR, "index.html"))
else:
    @app.get("/")
    def root():
        return {"status": "ok", "message": "Static frontend not found. Add a 'static' folder with index.html."}
=======


   prediction = "AI_GENERATED" if confidence > 0.6 else "HUMAN"

return {
    "prediction": prediction,
    "confidence": round(confidence, 2)
}


>>>>>>> 40268a2ed6bdf996d8bf4e32ca3f8ba88e3e81f3

from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel
import base64, io
import numpy as np
import soundfile as sf
import librosa

app = FastAPI()

API_KEY = "team_hcl_2026_key"

class VoiceRequest(BaseModel):
    language: str
    audio_format: str
    audio_base64: str

@app.get("/")
def root():
    return {"status": "ok"}

@app.post("/detect-voice")
def detect_voice(
    data: VoiceRequest,
    x_api_key: str = Header(...)
):
    if x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API Key")

    try:
        audio_bytes = base64.b64decode(data.audio_base64)
        audio, sr = sf.read(io.BytesIO(audio_bytes))
    except:
        raise HTTPException(status_code=400, detail="Invalid audio")

    mfcc = np.mean(librosa.feature.mfcc(y=audio, sr=sr))
    zcr = np.mean(librosa.feature.zero_crossing_rate(audio))

    score = mfcc + zcr
    confidence = float(1 / (1 + np.exp(-score)))

    prediction = "AI_GENERATED" if confidence > 0.6 else "HUMAN"

    return {
        "prediction": prediction,
        "confidence": round(confidence, 2)
    }

# VoiceGuard ? AI Voice Detection (Frontend + Backend)

Combined web app: **VoiceGuard** frontend (HTML/CSS/JS) + FastAPI backend for language & AI vs human voice detection.

## Run the app

You **must** run the server from inside the `ai-voice-detection-` folder (the folder that contains `main.py`). Otherwise you get: **"Error loading ASGI app. Could not import module 'main'"**.

**If the browser says "Connection failed" or won't connect:**
1. Start the server first (double‑click `run.bat` or run `python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000` from the `ai-voice-detection-` folder).
2. Wait until you see "Uvicorn running on ..." in the terminal.
3. In the browser address bar type exactly: **http://127.0.0.1:8000** and press Enter (or use the link the run script prints).
4. Do not open `index.html` by double‑clicking it; always use the URL above.

**Option A ? Use the run script (easiest)**

- **Windows (double?click or CMD):** run `run.bat`
- **PowerShell:** `.\run.ps1`

**Option B ? Manual**

1. **Open a terminal and go into the project folder**

   ```bash
   cd path\to\ai-voice-detection-
   ```
   Example: `cd "C:\Users\DELL\OneDrive\Desktop\HCL Hackathon Folder\ai-voice-detection-"`

2. **Create a virtual environment (recommended)**

   ```bash
   python -m venv venv
   venv\Scripts\activate
   ```

3. **Install dependencies**

   ```bash
   pip install -r requirements.txt
   ```

4. **Start the server (must be run from inside ai-voice-detection-)**

   ```bash
   python -m uvicorn main:app --reload
   ```

5. **Open in browser (important)**

   - **Always open the app at:** [http://127.0.0.1:8000](http://127.0.0.1:8000)
   - Do **not** open `index.html` or `static/index.html` directly (file://). That causes **"Connection failed"** because the browser cannot call the API.
   - API health: [http://127.0.0.1:8000/api/health](http://127.0.0.1:8000/api/health)

## Features

- **Frontend:** Record or upload audio ? analyze ? see results (language placeholder, AI vs Human, confidence).
- **Backend:** `POST /api/detect-voice` with JSON `{ "language", "audio_format", "audio_base64" }` and header `x-api-key: team_hcl_2026_key`. Returns `{ "language": "English" | "Hindi (Devanagari)" | "Unknown", "prediction": "HUMAN" | "AI_GENERATED", "confidence": number }`. Language is detected from the audio (Whisper). Confidence is based on **speech continuity**: continuous speech = high, gaps/pauses = low.
- Frontend converts all audio to WAV (base64) before sending so the backend can read it with soundfile.

## Why did it always show English?

If Hindi was always showing as English, common causes were:

1. **Exception in Whisper** ? Any error (e.g. missing dependency, bad audio) was caught and the app defaulted to "English". **Fix:** The server now logs the real error and the detected language code. Run `uvicorn main:app --reload` and watch the terminal for `Whisper detected language code:` and any traceback.
2. **Audio too short** ? Whisper needs enough audio for language detection. **Fix:** Audio is now padded/trimmed to 30 seconds with `whisper.pad_or_trim()`.
3. **"Tiny" model weak on Hindi** ? The tiny model often prefers English. **Fix:** The app now uses the **base** model for better Hindi (Devanagari) detection.

After pulling these changes, reinstall if needed (`pip install -r requirements.txt`) and restart the server. Check the console output when you analyze audio to see the raw language code Whisper returns.

## Train the AI vs Human model (for best results)

By default the app uses a **research-based heuristic** (energy and pitch variation, spectral flatness) so results are reasonable for real speech. If you want **better accuracy**, train on your own data:

1. Create folders `data/human/` and `data/ai/`.
2. Put **real human** voice WAV/MP3 in `data/human/`.
3. Put **AI or TTS** voice WAV/MP3 in `data/ai/`.
4. Run: `python train_model.py`
5. Restart the server. The app will then use your trained model (a flag file is created only when you train on real data).

If you train without real data (synthetic only), the app keeps using the heuristic so results stay reliable.

## Project layout

- `main.py` — FastAPI app, API routes, serves `static/`
- `static/` — Frontend: `index.html`, `styles.css`, `script.js`
- `audio_features.py` — Feature extraction for AI/Human classifier
- `train_model.py` — Train and save the AI vs Human model
- `models/` — Saved model and scaler (created by `train_model.py`)
- `data/human/`, `data/ai/` — Optional: your WAV/MP3 for training
- `requirements.txt` — Python dependencies

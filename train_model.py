"""
Train AI vs Human voice classifier.
- If data/human/ and data/ai/ exist with .wav files, trains on those.
- Otherwise generates synthetic training data and trains a model.
Saves model and scaler to models/ for use by main.py.
"""
import os
import sys
import numpy as np
import librosa
import joblib
from pathlib import Path

# Add project root
sys.path.insert(0, str(Path(__file__).resolve().parent))
from audio_features import extract_features

MODEL_DIR = Path(__file__).resolve().parent / "models"
MODEL_PATH = MODEL_DIR / "ai_voice_model.joblib"
SCALER_PATH = MODEL_DIR / "ai_voice_scaler.joblib"
REAL_DATA_FLAG = MODEL_DIR / "trained_on_real_data.flag"
SR = 22050
N_SAMPLES = SR * 3  # 3 seconds per synthetic sample
N_SYNTHETIC = 80   # per class when using synthetic data


def load_audio_files(folder: Path, sr: int = SR):
    """Load all .wav files from folder; return list of (audio, sr)."""
    audios = []
    if not folder.is_dir():
        return audios
    for f in folder.glob("*.wav"):
        try:
            y, s = librosa.load(f, sr=sr, mono=True, duration=10.0)
            audios.append((y, s))
        except Exception as e:
            print(f"Skip {f}: {e}")
    for f in folder.glob("*.mp3"):
        try:
            y, s = librosa.load(f, sr=sr, mono=True, duration=10.0)
            audios.append((y, s))
        except Exception as e:
            print(f"Skip {f}: {e}")
    return audios


def generate_synthetic_human(sr: int, n: int) -> list:
    """Generate synthetic 'human-like' audio: varied, some noise, dynamic range."""
    out = []
    rng = np.random.default_rng(42)
    for _ in range(n):
        length = rng.integers(SR * 2, SR * 4)
        t = np.linspace(0, length / sr, length, dtype=np.float32)
        # Mix of tones + noise (speech-like spectrum)
        freqs = rng.uniform(200, 800, 5)
        y = np.zeros(length, dtype=np.float32)
        for f in freqs:
            y += rng.uniform(0.1, 0.3) * np.sin(2 * np.pi * f * t + rng.uniform(0, 2 * np.pi))
        y += rng.uniform(-0.05, 0.05, size=length).astype(np.float32)
        # Vary amplitude over time (like speech)
        envelope = 0.5 + 0.5 * np.sin(np.linspace(0, 8 * np.pi, length))
        y = y * envelope
        y = y / (np.max(np.abs(y)) + 1e-8)
        out.append((y, sr))
    return out


def generate_synthetic_ai(sr: int, n: int) -> list:
    """Generate synthetic 'AI-like' audio: very smooth, uniform, less variation."""
    out = []
    rng = np.random.default_rng(43)
    for _ in range(n):
        length = N_SAMPLES
        t = np.linspace(0, length / sr, length, dtype=np.float32)
        # Fewer, cleaner components (TTS tends to be smoother)
        freqs = rng.uniform(300, 600, 3)
        y = np.zeros(length, dtype=np.float32)
        for f in freqs:
            y += 0.3 * np.sin(2 * np.pi * f * t)
        y += rng.uniform(-0.02, 0.02, size=length).astype(np.float32)  # less noise
        # Flatter envelope (more uniform)
        y = y / (np.max(np.abs(y)) + 1e-8)
        out.append((y, sr))
    return out


def main():
    project_root = Path(__file__).resolve().parent
    data_human = project_root / "data" / "human"
    data_ai = project_root / "data" / "ai"

    X_list = []
    y_list = []

    human_audios = load_audio_files(data_human)
    ai_audios = load_audio_files(data_ai)

    if human_audios and ai_audios:
        print("Training on real data: data/human/ and data/ai/")
        for audio, sr in human_audios:
            try:
                X_list.append(extract_features(audio, sr))
                y_list.append(0)  # HUMAN
            except Exception as e:
                print(f"Skip human sample: {e}")
        for audio, sr in ai_audios:
            try:
                X_list.append(extract_features(audio, sr))
                y_list.append(1)  # AI_GENERATED
            except Exception as e:
                print(f"Skip AI sample: {e}")
    else:
        print("No data/human/ or data/ai/ found. Using synthetic data.")
        for audio, sr in generate_synthetic_human(SR, N_SYNTHETIC):
            X_list.append(extract_features(audio, sr))
            y_list.append(0)
        for audio, sr in generate_synthetic_ai(SR, N_SYNTHETIC):
            X_list.append(extract_features(audio, sr))
            y_list.append(1)

    X = np.stack(X_list)
    y = np.array(y_list)
    print(f"Training set: {X.shape[0]} samples, {X.shape[1]} features")

    from sklearn.preprocessing import StandardScaler
    from sklearn.ensemble import RandomForestClassifier

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)
    clf = RandomForestClassifier(n_estimators=100, max_depth=12, random_state=42, n_jobs=-1)
    clf.fit(X_scaled, y)
    train_acc = (clf.predict(X_scaled) == y).mean()
    print(f"Train accuracy: {train_acc:.2%}")

    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    joblib.dump(clf, MODEL_PATH)
    joblib.dump(scaler, SCALER_PATH)
    trained_on_real = bool(human_audios and ai_audios)
    if trained_on_real:
        REAL_DATA_FLAG.touch()
        print("Saved trained_on_real_data.flag (app will use this model)")
    elif REAL_DATA_FLAG.is_file():
        REAL_DATA_FLAG.unlink()
        print("Removed flag (trained on synthetic data; app will use heuristic until you train on real data)")
    print(f"Saved model to {MODEL_PATH}")
    print(f"Saved scaler to {SCALER_PATH}")


if __name__ == "__main__":
    main()

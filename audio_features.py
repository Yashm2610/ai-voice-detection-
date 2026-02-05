"""
Feature extraction for AI vs Human voice classification.
Returns a fixed-size vector: MFCC stats, ZCR, spectral features, etc.
"""
import numpy as np
import librosa


def extract_features(audio: np.ndarray, sr: int, n_mfcc: int = 13) -> np.ndarray:
    """
    Extract a fixed-size feature vector from audio for AI/Human classification.
    Uses MFCC (mean/std), ZCR, spectral centroid, rolloff, contrast, RMS.
    """
    if audio.ndim > 1:
        audio = np.mean(audio, axis=1)
    if len(audio) < sr // 2:
        audio = np.pad(audio, (0, max(0, sr // 2 - len(audio))), mode="constant")

    features = []

    # MFCC (mean and std across time)
    mfcc = librosa.feature.mfcc(y=audio, sr=sr, n_mfcc=n_mfcc, n_fft=2048, hop_length=512)
    features.extend(np.mean(mfcc, axis=1))
    features.extend(np.std(mfcc, axis=1))

    # Delta MFCC (mean) - captures dynamics
    mfcc_delta = librosa.feature.delta(mfcc)
    features.extend(np.mean(mfcc_delta, axis=1))

    # Zero-crossing rate
    zcr = librosa.feature.zero_crossing_rate(audio, frame_length=2048, hop_length=512)
    features.append(np.mean(zcr))
    features.append(np.std(zcr))

    # Spectral centroid
    cent = librosa.feature.spectral_centroid(y=audio, sr=sr, n_fft=2048, hop_length=512)
    features.append(np.mean(cent))
    features.append(np.std(cent))

    # Spectral rolloff
    rolloff = librosa.feature.spectral_rolloff(y=audio, sr=sr, n_fft=2048, hop_length=512)
    features.append(np.mean(rolloff))
    features.append(np.std(rolloff))

    # Spectral contrast
    contrast = librosa.feature.spectral_contrast(y=audio, sr=sr, n_fft=2048, hop_length=512)
    features.append(np.mean(contrast))
    features.append(np.std(contrast))

    # RMS energy
    rms = librosa.feature.rms(y=audio, frame_length=2048, hop_length=512)
    features.append(np.mean(rms))
    features.append(np.std(rms))

    # Chroma (mean) - pitch class distribution
    chroma = librosa.feature.chroma_stft(y=audio, sr=sr, n_fft=2048, hop_length=512)
    features.extend(np.mean(chroma, axis=1))

    vec = np.array(features, dtype=np.float32)
    # Replace any nan/inf for robustness
    vec = np.nan_to_num(vec, nan=0.0, posinf=0.0, neginf=0.0)
    return vec

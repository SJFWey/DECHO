import os
from typing import Any, Dict, List, Optional

import numpy as np
import soundfile as sf
import yaml

try:
    import sherpa_onnx
except ImportError:
    print("sherpa-onnx not found. Please install it with: pip install sherpa-onnx")
    sherpa_onnx = None


def _resample_audio(
    audio: np.ndarray, source_rate: int, target_rate: int
) -> np.ndarray:
    """
    Resamples the provided waveform to the desired sample rate using linear interpolation.

    Args:
        audio (np.ndarray): Input mono waveform as a 1-D array.
        source_rate (int): Original sample rate.
        target_rate (int): Target sample rate.

    Returns:
        np.ndarray: Resampled waveform with dtype float32.
    """
    if source_rate == target_rate or audio.size == 0:
        return audio.astype(np.float32, copy=False)

    duration_seconds = audio.shape[0] / float(source_rate)
    target_length = max(1, int(round(duration_seconds * target_rate)))
    if audio.shape[0] == 1:
        return np.full(target_length, float(audio[0]), dtype=np.float32)

    original_indices = np.arange(audio.shape[0], dtype=np.float64)
    target_indices = np.linspace(
        0.0,
        audio.shape[0] - 1,
        target_length,
        dtype=np.float64,
    )
    resampled = np.interp(target_indices, original_indices, audio).astype(np.float32)
    return resampled


def _find_split_points(
    audio: np.ndarray, sample_rate: int, chunk_duration_sec: int = 60
) -> List[int]:
    """
    Finds indices to split audio at silence points near chunk boundaries.
    Returns a list of sample indices including 0 and len(audio).
    """
    total_samples = len(audio)
    chunk_samples = chunk_duration_sec * sample_rate

    split_points = [0]
    current_start = 0

    while current_start + chunk_samples < total_samples:
        # Search window: from (target - 15s) to (target + 15s)
        # We want to find the quietest point in [current_start + 45s, current_start + 75s]
        search_start = current_start + int(chunk_samples * 0.75)  # ~45s
        search_end = min(
            current_start + int(chunk_samples * 1.25), total_samples
        )  # ~75s

        if search_start >= total_samples:
            break

        # Extract the segment to search
        segment = audio[search_start:search_end]

        if len(segment) == 0:
            break

        # Calculate amplitude envelope (simple absolute value)
        # We look for the quietest 0.1s window
        window_size = int(0.1 * sample_rate)
        num_windows = len(segment) // window_size

        if num_windows == 0:
            split_idx = search_end
        else:
            # Reshape to (num_windows, window_size) and take max over axis 1
            trunc_len = num_windows * window_size
            reshaped = np.abs(segment[:trunc_len]).reshape(num_windows, window_size)
            energies = np.max(reshaped, axis=1)

            # Find the window with minimum energy
            min_energy_idx = np.argmin(energies)

            # The split point is the middle of that window
            split_offset = (min_energy_idx * window_size) + (window_size // 2)
            split_idx = search_start + split_offset

        split_points.append(split_idx)
        current_start = split_idx

    split_points.append(total_samples)
    return sorted(list(set(split_points)))


class ParakeetASR:
    def __init__(self, model_dir: Optional[str] = None) -> None:
        """
        Initialize the Parakeet ASR engine with the configured model directory.

        Args:
            model_dir (Optional[str]): Custom path to the Parakeet ONNX bundle.
        """
        if not sherpa_onnx:
            raise ImportError("sherpa-onnx is required for Parakeet ASR.")

        if model_dir is None:
            with open("config.yaml", "r", encoding="utf-8") as f:
                config = yaml.safe_load(f)
                model_dir = config.get("asr", {}).get(
                    "parakeet_model_dir",
                    "models/sherpa-onnx-nemo-parakeet-tdt-0.6b-v3-int8",
                )

        self.model_dir = model_dir
        self.expected_sample_rate = 16000
        self._init_recognizer()

    def _init_recognizer(self) -> None:
        """
        Build the sherpa-onnx OfflineRecognizer from NeMo transducer components.
        """
        if sherpa_onnx is None:
            raise ImportError("sherpa-onnx is not installed")

        encoder_path = os.path.join(self.model_dir, "encoder.int8.onnx")
        decoder_path = os.path.join(self.model_dir, "decoder.int8.onnx")
        joiner_path = os.path.join(self.model_dir, "joiner.int8.onnx")
        tokens_path = os.path.join(self.model_dir, "tokens.txt")

        if not os.path.exists(encoder_path):
            raise FileNotFoundError(f"Encoder model not found at {encoder_path}")
        if not os.path.exists(decoder_path):
            raise FileNotFoundError(f"Decoder model not found at {decoder_path}")
        if not os.path.exists(joiner_path):
            raise FileNotFoundError(f"Joiner model not found at {joiner_path}")
        if not os.path.exists(tokens_path):
            raise FileNotFoundError(f"Tokens file not found at {tokens_path}")

        self.recognizer = sherpa_onnx.OfflineRecognizer.from_transducer(
            encoder=encoder_path,
            decoder=decoder_path,
            joiner=joiner_path,
            tokens=tokens_path,
            num_threads=4,
            provider="cpu",
            model_type="nemo_transducer",
        )

    def transcribe(self, audio_file: str) -> Dict[str, Any]:
        """
        Run offline ASR for the provided audio path.

        Args:
            audio_file (str): Path to the audio file.

        Returns:
            Dict[str, Any]: Transcription output containing text, timestamps, and tokens.
        """
        if not os.path.exists(audio_file):
            raise FileNotFoundError(f"Audio file not found: {audio_file}")

        audio, sample_rate = sf.read(audio_file, dtype="float32")

        print(
            f"[DEBUG] Original audio shape: {audio.shape}, dtype: {audio.dtype}, sample_rate: {sample_rate}Hz"
        )

        if len(audio.shape) > 1 and audio.shape[1] > 1:
            print(
                f"[DEBUG] Converting stereo audio (channels={audio.shape[1]}) to mono"
            )
            audio = np.mean(audio, axis=1)

        audio = audio.flatten()
        audio = np.nan_to_num(audio, nan=0.0, posinf=0.0, neginf=0.0)

        if audio.size == 0:
            raise ValueError("Loaded audio file contains no samples.")

        if sample_rate != self.expected_sample_rate:
            print(
                f"[INFO] Resampling audio from {sample_rate}Hz to {self.expected_sample_rate}Hz."
            )
            audio = _resample_audio(audio, sample_rate, self.expected_sample_rate)
            sample_rate = self.expected_sample_rate

        if audio.dtype != np.float32:
            audio = audio.astype(np.float32)

        print(f"[DEBUG] Processed audio shape: {audio.shape}, dtype: {audio.dtype}")

        # If audio is longer than 60 seconds (16000 * 60 samples), use chunked processing
        if len(audio) > 60 * sample_rate:
            print("[INFO] Audio is long (>60s), using chunked processing.")
            return self._transcribe_long_audio(audio, sample_rate)

        stream = self.recognizer.create_stream()
        stream.accept_waveform(sample_rate, audio)
        self.recognizer.decode_stream(stream)
        result = stream.result

        print(f"[DEBUG] Transcription result: {result.text}")

        return {
            "text": result.text,
            "timestamps": result.timestamps,
            "tokens": result.tokens,
        }

    def _transcribe_long_audio(
        self, audio: np.ndarray, sample_rate: int
    ) -> Dict[str, Any]:
        """
        Process long audio by splitting into chunks at silence points.
        """
        split_indices = _find_split_points(audio, sample_rate, chunk_duration_sec=60)

        full_text_parts = []
        all_tokens = []
        all_timestamps = []

        # Process each chunk
        for i in range(len(split_indices) - 1):
            start_idx = split_indices[i]
            end_idx = split_indices[i + 1]
            chunk = audio[start_idx:end_idx]

            if len(chunk) < 1600:  # Skip tiny chunks (< 0.1s)
                continue

            print(
                f"[DEBUG] Processing chunk {i + 1}/{len(split_indices) - 1}: {len(chunk) / sample_rate:.2f}s"
            )

            stream = self.recognizer.create_stream()
            stream.accept_waveform(sample_rate, chunk)
            self.recognizer.decode_stream(stream)
            result = stream.result

            if result.text:
                full_text_parts.append(result.text)

            # Adjust timestamps by adding the start time offset
            time_offset = start_idx / sample_rate
            if hasattr(result, "timestamps") and result.timestamps:
                adjusted_timestamps = [t + time_offset for t in result.timestamps]
                all_timestamps.extend(adjusted_timestamps)

            if hasattr(result, "tokens") and result.tokens:
                all_tokens.extend(result.tokens)

        full_text = " ".join(full_text_parts)
        return {"text": full_text, "timestamps": all_timestamps, "tokens": all_tokens}


def transcribe_audio(audio_path: str) -> Dict[str, Any]:
    """
    Convenience helper to instantiate ParakeetASR and run transcription.

    Args:
        audio_path (str): Path to the input audio file.

    Returns:
        Dict[str, Any]: Structured transcription output.
    """
    asr = ParakeetASR()
    return asr.transcribe(audio_path)

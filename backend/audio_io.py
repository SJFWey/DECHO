import logging
import os
from typing import Optional

import numpy as np
import soundfile as sf

logger = logging.getLogger(__name__)

try:
    import sounddevice as sd
except ImportError:
    logger.warning(
        "sounddevice not found. Audio recording/playback will not work. Install with: pip install sounddevice"
    )
    sd = None


class AudioRecorder:
    """
    Handles audio recording from the default system microphone.
    """

    def __init__(self, sample_rate: int = 16000, channels: int = 1):
        self.sample_rate = sample_rate
        self.channels = channels
        self.recording = False
        self.frames = []
        self._stream = None

    def start_recording(self):
        """Start recording audio in a non-blocking way."""
        if sd is None:
            raise ImportError("sounddevice is required for recording.")

        if self.recording:
            logger.warning("Already recording.")
            return

        self.frames = []
        self.recording = True

        def callback(indata, frames, time_info, status):
            if status:
                logger.warning(f"Audio callback status: {status}")
            self.frames.append(indata.copy())

        try:
            self._stream = sd.InputStream(
                samplerate=self.sample_rate, channels=self.channels, callback=callback
            )
            self._stream.start()
            logger.info("Recording started...")
        except Exception as e:
            self.recording = False
            logger.error(f"Failed to start recording: {e}")
            raise

    def stop_recording(self, output_path: str) -> Optional[str]:
        """
        Stop recording and save to file.

        Args:
            output_path: Path to save the WAV file.

        Returns:
            str: The path to the saved file, or None if failed.
        """
        if not self.recording or not self._stream:
            return None

        self._stream.stop()
        self._stream.close()
        self.recording = False
        logger.info("Recording stopped.")

        if not self.frames:
            logger.warning("No audio data recorded.")
            return None

        # Concatenate all frames
        audio_data = np.concatenate(self.frames, axis=0)

        # Save to file
        try:
            os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
            sf.write(output_path, audio_data, self.sample_rate)
            logger.info(f"Audio saved to {output_path}")
            return output_path
        except Exception as e:
            logger.error(f"Failed to save recording: {e}")
            return None


class AudioPlayer:
    """
    Handles audio playback using the default system speakers.
    """

    def __init__(self):
        self._stream = None
        self.playing = False

    def play_file(self, file_path: str, block: bool = False):
        """
        Play an audio file.

        Args:
            file_path: Path to the audio file.
            block: If True, wait until playback finishes.
        """
        if sd is None:
            raise ImportError("sounddevice is required for playback.")

        if not os.path.exists(file_path):
            logger.error(f"File not found: {file_path}")
            return

        try:
            data, fs = sf.read(file_path)
            logger.info(f"Playing {file_path} ({len(data)/fs:.2f}s)")

            self.playing = True
            sd.play(data, fs)

            if block:
                sd.wait()
                self.playing = False

        except Exception as e:
            logger.error(f"Failed to play audio: {e}")
            self.playing = False

    def stop(self):
        """Stop current playback."""
        if sd is None:
            return
        sd.stop()
        self.playing = False
        logger.info("Playback stopped.")


# Singleton instances for easy access
recorder = AudioRecorder()
player = AudioPlayer()

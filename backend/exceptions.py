class HearingError(Exception):
    """Base exception for all Hearing application errors."""


class AudioConversionError(HearingError):
    """Raised when audio conversion fails."""


class ASRError(HearingError):
    """Raised when ASR transcription fails."""


class NLPError(HearingError):
    """Raised when NLP processing fails."""


class ConfigError(HearingError):
    """Raised when configuration is invalid or missing."""

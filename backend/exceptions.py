class DECHOError(Exception):
    """Base exception for all DECHO application errors."""


class AudioConversionError(DECHOError):
    """Raised when audio conversion fails."""


class ASRError(DECHOError):
    """Raised when ASR transcription fails."""


class NLPError(DECHOError):
    """Raised when NLP processing fails."""


class ConfigError(DECHOError):
    """Raised when configuration is invalid or missing."""

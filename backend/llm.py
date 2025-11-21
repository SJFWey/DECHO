import io
import json
import logging
import os
import wave
from typing import Any, Dict, List, Optional

import requests
from google import genai
from google.genai import types

from backend.utils import load_config

logger = logging.getLogger(__name__)


def chat_completion(
    messages: List[Dict[str, str]],
    model: Optional[str] = None,
    api_key: Optional[str] = None,
    base_url: Optional[str] = None,
    raise_on_error: bool = False,
) -> Optional[Dict[str, Any]]:
    """
    Sends a chat completion request to the LLM API.

    Args:
        messages (List[Dict[str, str]]): List of message dictionaries.
        model (Optional[str]): Model name to use. Defaults to config.
        api_key (Optional[str]): API key to use. Defaults to config/env.
        base_url (Optional[str]): Base URL to use. Defaults to config.
        raise_on_error (bool): Whether to raise an exception on error.

    Returns:
        Optional[Dict[str, Any]]: The JSON response from the API, or None if failed.
    """
    config = load_config()
    llm_config = config.get("llm", {})

    # Prioritize argument -> environment variable -> config
    api_key = api_key or os.getenv("LLM_API_KEY") or llm_config.get("api_key")
    base_url = base_url or llm_config.get("base_url", "https://example-llm-provider.com/v1")
    if base_url:
        base_url = base_url.rstrip("/")
    default_model = llm_config.get("model", "openai/gpt-4o")

    if not api_key:
        logger.error(
            "LLM API Key not found. Please set LLM_API_KEY env var or config.yaml."
        )
        raise ValueError("LLM API Key not found")

    url = f"{base_url}/chat/completions"

    headers = {
        "Authorization": f"Bearer {api_key}",
        "HTTP-Referer": "http://localhost:8501",  # Localhost for streamlit
        "X-Title": "Hearing App",
        "Content-Type": "application/json",
    }

    data = {"model": model or default_model, "messages": messages}

    response = None
    try:
        response = requests.post(url, headers=headers, data=json.dumps(data))
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        logger.error(f"LLM Request failed: {e}")
        if response:
            logger.error(f"Response: {response.text}")

        if raise_on_error:
            raise e

        return None


def split_text_by_meaning(text: str, max_length: int = 80) -> List[str]:
    """
    Uses LLM to split text into meaningful segments.

    Args:
        text (str): The text to split.
        max_length (int): Target maximum length for segments.

    Returns:
        List[str]: List of text segments.
    """
    prompt = f"""
    Split the following German text into smaller, meaningful segments for subtitle generation.
    
    Rules:
    1. **Sentence Flow Completeness**: Ensure each segment is a complete thought or a fluent phrase. Do not break the flow abruptly.
    2. **Maximum Chunk Size**: A single complete sentence is the MAXIMUM size for a chunk. Never combine multiple sentences into one chunk.
    3. **Splitting Long Sentences**: If a sentence is too long (>{max_length} chars), split it at natural pauses (commas, conjunctions) to maintain fluency.
    4. **No Grammar Correction**: Do NOT correct grammar errors.
    5. **Spelling Correction**: Correct obvious spelling mistakes from ASR.
    6. **Output Format**: Return a JSON list of strings. When joined, they should match the original text content.
    
    Text: "{text}"
    """

    messages = [
        {
            "role": "system",
            "content": "You are a helpful assistant that splits text into subtitles.",
        },
        {"role": "user", "content": prompt},
    ]

    response = chat_completion(messages)
    if response:
        # Safely access response structure with validation
        if "choices" in response and len(response["choices"]) > 0:
            choice = response["choices"][0]
            if "message" in choice and "content" in choice["message"]:
                content = choice["message"]["content"]
            else:
                logger.warning("LLM response missing 'message' or 'content' field")
                return [text]
        else:
            logger.warning("LLM response missing 'choices' field or empty")
            return [text]

        # Try to parse JSON from the response
        try:
            # Clean up code blocks if present
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1].split("```")[0]

            return json.loads(content.strip())
        except json.JSONDecodeError:
            logger.warning(
                "Failed to parse LLM response as JSON. Returning original text."
            )
            return [text]
    return [text]


def convert_pcm_to_wav(pcm_data: bytes, sample_rate: int = 24000) -> bytes:
    """
    Converts raw PCM data to WAV format bytes.
    Gemini TTS returns PCM 24kHz, 1 channel, 16-bit.
    """
    with io.BytesIO() as wav_buffer:
        with wave.open(wav_buffer, "wb") as wf:
            wf.setnchannels(1)  # Mono
            wf.setsampwidth(2)  # 16-bit
            wf.setframerate(sample_rate)
            wf.writeframes(pcm_data)
        return wav_buffer.getvalue()


def tts_llm(text: str, options: Optional[Dict[str, Any]] = None) -> Optional[bytes]:
    """
    Generates speech from text using Gemini TTS model.

    Args:
        text (str): The text to convert to speech.
        options (Optional[Dict[str, Any]]): Custom options to override defaults.

    Returns:
        Optional[bytes]: The generated audio bytes, or None if failed.
    """
    config = load_config()
    tts_config = config.get("tts", {})

    # Merge defaults with user options
    defaults = tts_config.get("defaults", {})
    user_options = options or {}

    # language = user_options.get("language", defaults.get("language", "de-DE")) # Not used in API directly yet, but good for future
    speed = user_options.get(
        "speed", defaults.get("speed", "Native conversational pace")
    )
    tone = user_options.get(
        "tone", defaults.get("tone", "Clear, educational, engaging")
    )

    # API Key and Model
    api_key = (
        user_options.get("api_key")
        or os.getenv("TTS_API_KEY")
        or tts_config.get("api_key")
    )
    model_name = user_options.get("model") or tts_config.get(
        "model", "gemini-2.5-flash-preview-tts"
    )

    if not api_key:
        logger.error(
            "TTS API Key not found. Please set TTS_API_KEY env var or config.yaml."
        )
        raise ValueError("TTS API Key not found")

    client = genai.Client(api_key=api_key)

    # Determine Mode (Single vs Multi-speaker)
    is_multi_speaker = "Redner1" in text and "Redner2" in text

    voice_map = tts_config.get("voice_map", {"male": "Orus", "female": "Kore"})
    male_voice = voice_map.get("male", "Orus")
    female_voice = voice_map.get("female", "Kore")

    # Construct Prompt
    system_instruction = (
        f"Please read the following German text at a {speed} pace with a {tone} tone.\n"
    )
    if is_multi_speaker:
        system_instruction += "The conversation is between Redner1 and Redner2.\n"

    full_prompt = f"{system_instruction}---\n{text}"

    try:
        speech_config = None
        if is_multi_speaker:
            speech_config = types.SpeechConfig(
                multi_speaker_voice_config=types.MultiSpeakerVoiceConfig(
                    speaker_voice_configs=[
                        types.SpeakerVoiceConfig(
                            speaker="Redner1",
                            voice_config=types.VoiceConfig(
                                prebuilt_voice_config=types.PrebuiltVoiceConfig(
                                    voice_name=male_voice
                                )
                            ),
                        ),
                        types.SpeakerVoiceConfig(
                            speaker="Redner2",
                            voice_config=types.VoiceConfig(
                                prebuilt_voice_config=types.PrebuiltVoiceConfig(
                                    voice_name=female_voice
                                )
                            ),
                        ),
                    ]
                )
            )
        else:
            # Default single speaker (Male)
            # Check if user specified voice in options, otherwise use default male
            voice_name = user_options.get("voice", male_voice)
            speech_config = types.SpeechConfig(
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(
                        voice_name=voice_name
                    )
                )
            )

        response = client.models.generate_content(
            model=model_name,
            contents=full_prompt,
            config=types.GenerateContentConfig(
                response_modalities=["AUDIO"],
                speech_config=speech_config,
                automatic_function_calling=types.AutomaticFunctionCallingConfig(
                    maximum_remote_calls=14
                ),
            ),
        )

        if (
            response.candidates
            and response.candidates[0].content
            and response.candidates[0].content.parts
        ):
            part = response.candidates[0].content.parts[0]
            if part.inline_data and part.inline_data.data:
                return convert_pcm_to_wav(part.inline_data.data)
        return None

    except Exception as e:
        logger.error(f"TTS Generation failed: {e}")
        raise e

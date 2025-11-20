import json
import logging
import os
from typing import Any, Dict, List, Optional

import requests

from backend.utils import load_config

logger = logging.getLogger(__name__)


def chat_completion(
    messages: List[Dict[str, str]],
    model: Optional[str] = None,
    api_key: Optional[str] = None,
    base_url: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """
    Sends a chat completion request to the LLM API.

    Args:
        messages (List[Dict[str, str]]): List of message dictionaries.
        model (Optional[str]): Model name to use. Defaults to config.
        api_key (Optional[str]): API key to use. Defaults to config/env.
        base_url (Optional[str]): Base URL to use. Defaults to config.

    Returns:
        Optional[Dict[str, Any]]: The JSON response from the API, or None if failed.
    """
    config = load_config()
    llm_config = config.get("llm", {})

    # Prioritize argument -> environment variable -> config
    api_key = api_key or os.getenv("LLM_API_KEY") or llm_config.get("api_key")
    base_url = base_url or llm_config.get("base_url", "https://example-llm-provider.com/v1")
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
    Split the following text into smaller, meaningful segments for subtitle generation.
    
    IMPORTANT: 
    1. Do **NOT** correct any grammar errors.
    2. Correct spelling mistakes, since the text was transcribed by ASR.
    3. Prefer to split at natural pauses like commas, periods, or punctuation. (suitable for language learning.)
    4. The output must be a JSON list of strings that, when joined, exactly matches the input text (ignoring whitespace).
    
    Each segment should be roughly under {max_length} characters if possible, but prioritize meaning.
    Return the result as a JSON list of strings.
    
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
        content = response["choices"][0]["message"]["content"]
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

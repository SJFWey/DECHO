from fastapi import APIRouter, HTTPException
from server.schemas import ConfigResponse, ConfigUpdate
from backend.utils import load_config
from backend.exceptions import ConfigError

router = APIRouter()


@router.get("/", response_model=ConfigResponse)
async def get_config():
    try:
        config = load_config()
        # Mask sensitive information
        # if "llm" in config and "api_key" in config["llm"]:
        #     config["llm"]["api_key"] = "********"
        return config
    except ConfigError as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/", response_model=ConfigResponse)
async def update_config(config_update: ConfigUpdate):
    """
    Configuration is now managed via environment variables (.env file).
    This endpoint is deprecated and returns a helpful message.
    """
    raise HTTPException(
        status_code=400,
        detail="Configuration updates are no longer supported via API. "
        "Please update your .env file and restart the application.",
    )


@router.post("/test-llm")
async def test_llm(config_update: ConfigUpdate):
    """
    Test the LLM connection with the provided configuration.
    """
    try:
        from backend.llm import chat_completion

        api_key = config_update.llm.api_key if config_update.llm else None
        # If api_key is masked, try to load from current config
        if api_key == "********":
            current_config = load_config()
            api_key = current_config.get("llm", {}).get("api_key")

        base_url = config_update.llm.base_url if config_update.llm else None
        model = config_update.llm.model if config_update.llm else None

        messages = [{"role": "user", "content": "Hello, are you working?"}]

        response = chat_completion(
            messages=messages,
            model=model,
            api_key=api_key,
            base_url=base_url,
            raise_on_error=True,
        )

        if response:
            return {
                "status": "success",
                "message": "Connection successful",
                "response": response,
            }
        else:
            raise HTTPException(status_code=500, detail="LLM returned no response")

    except Exception as e:
        # Include the actual error message in the response
        error_detail = str(e)
        if hasattr(e, "response") and e.response is not None:
            try:
                error_detail += f" - Response: {e.response.text}"
            except Exception:
                pass
        raise HTTPException(status_code=500, detail=error_detail)


@router.post("/test-tts")
async def test_tts(config_update: ConfigUpdate):
    """
    Test the TTS connection with the provided configuration.
    """
    try:
        from backend.llm import tts_llm

        api_key = config_update.tts.api_key if config_update.tts else None
        # If api_key is masked, try to load from current config
        if api_key == "********":
            current_config = load_config()
            api_key = current_config.get("tts", {}).get("api_key")

        model = config_update.tts.model if config_update.tts else None

        # Use defaults from request or config
        defaults = config_update.tts.defaults if config_update.tts else None

        options = {
            "api_key": api_key,
            "model": model,
        }

        if defaults:
            options.update(defaults.model_dump())

        # Test with a short text
        audio_bytes = tts_llm("Hello, this is a test.", options=options)

        if audio_bytes:
            return {
                "status": "success",
                "message": "Connection successful",
            }
        else:
            raise HTTPException(status_code=500, detail="TTS returned no audio")

    except Exception as e:
        # Include the actual error message in the response
        error_detail = str(e)
        if hasattr(e, "response") and e.response is not None:
            try:
                error_detail += f" - Response: {e.response.text}"
            except Exception:
                pass
        raise HTTPException(
            status_code=500, detail=f"TTS Connection failed: {error_detail}"
        )

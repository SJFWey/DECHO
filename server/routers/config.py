from fastapi import APIRouter, HTTPException
from server.schemas import ConfigResponse, ConfigUpdate
from backend.utils import load_config, save_config
from backend.exceptions import ConfigError

router = APIRouter()


@router.get("/", response_model=ConfigResponse)
async def get_config():
    try:
        config = load_config()
        # Mask sensitive information
        if "llm" in config and "api_key" in config["llm"]:
            config["llm"]["api_key"] = "********"
        return config
    except ConfigError as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/", response_model=ConfigResponse)
async def update_config(config_update: ConfigUpdate):
    try:
        current_config = load_config()

        # Update fields if provided
        if config_update.asr:
            current_config["asr"].update(
                config_update.asr.model_dump(exclude_unset=True)
            )

        if config_update.llm:
            if "llm" not in current_config:
                current_config["llm"] = {}
            current_config["llm"].update(
                config_update.llm.model_dump(exclude_unset=True)
            )

        if config_update.app:
            current_config["app"].update(
                config_update.app.model_dump(exclude_unset=True)
            )

        save_config(current_config)
        return current_config
    except ConfigError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to update config: {str(e)}"
        )


@router.post("/test-llm")
async def test_llm(config_update: ConfigUpdate):
    """
    Test the LLM connection with the provided configuration.
    """
    try:
        from backend.llm import chat_completion

        api_key = config_update.llm.api_key if config_update.llm else None
        base_url = config_update.llm.base_url if config_update.llm else None
        model = config_update.llm.model if config_update.llm else None

        messages = [{"role": "user", "content": "Hello, are you working?"}]

        response = chat_completion(
            messages=messages, model=model, api_key=api_key, base_url=base_url
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
        raise HTTPException(status_code=500, detail=str(e))

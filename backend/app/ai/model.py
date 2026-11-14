from langchain.chat_models import init_chat_model

from backend.app.core.config import Settings


def create_model(settings: Settings):
    if settings.model_mode == "demo":
        return None
    return init_chat_model(
        settings.model_name,
        model_provider="openai",
        api_key=settings.openai_api_key.get_secret_value(),
        base_url=settings.openai_base_url,
        timeout=settings.model_timeout_seconds,
        max_retries=1,
    )

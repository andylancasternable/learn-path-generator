import os

from src.config import settings

GROQ_MODEL = "llama-3.3-70b-versatile"


def get_llm(temperature=None, max_tokens=None):
    """Return an LLM instance based on the LLM_PROVIDER environment variable.

    When LLM_PROVIDER=groq (case-insensitive) a ChatGroq instance is returned
    using the GROQ_API_KEY environment variable and the llama-3.3-70b-versatile
    model.  For any other value (or when the variable is absent) a ChatAnthropic
    instance is returned using ANTHROPIC_API_KEY.

    Returns None if the required API key for the selected provider is not set.
    """
    _temperature = temperature if temperature is not None else settings.temperature
    _max_tokens = max_tokens if max_tokens is not None else settings.max_tokens

    provider = os.getenv("LLM_PROVIDER", "anthropic").lower()

    if provider == "groq":
        groq_api_key = os.getenv("GROQ_API_KEY", "")
        if not groq_api_key:
            return None
        from langchain_groq import ChatGroq
        return ChatGroq(
            groq_api_key=groq_api_key,
            model_name=GROQ_MODEL,
            temperature=_temperature,
            max_tokens=_max_tokens,
        )

    # Default: anthropic
    api_key = os.getenv("ANTHROPIC_API_KEY") or settings.anthropic_api_key
    if not api_key:
        return None
    from langchain_anthropic import ChatAnthropic
    return ChatAnthropic(
        api_key=api_key,
        model_name=settings.model_name,
        temperature=_temperature,
        max_tokens=_max_tokens,
    )

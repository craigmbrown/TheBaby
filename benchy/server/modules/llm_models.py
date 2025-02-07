import llm
from dotenv import load_dotenv
import os
from modules import ollama_llm
from modules.data_types import (
    ModelAlias,
    PromptResponse,
    PromptWithToolCalls,
    ToolCallResponse,
)
from modules import openai_llm, gemini_llm, deepseek_llm
from utils import MAP_MODEL_ALIAS_TO_COST_PER_MILLION_TOKENS
from modules.tools import all_tools_list
from modules import anthropic_llm

# Load environment variables from .env file
load_dotenv()


def prompt(prompt_str: str, model_alias_str: str) -> PromptResponse:
    parts = model_alias_str.split(":", 1)
    if len(parts) < 2:
        raise ValueError("No provider prefix found in model string")
    provider = parts[0]
    model_name = parts[1]

    # For special predictive cases:
    if provider == "openai" and model_name in [
        "gpt-4o-predictive",
        "gpt-4o-mini-predictive",
    ]:
        # Remove -predictive suffix when passing to API
        clean_model_name = model_name.replace("-predictive", "")
        return openai_llm.predictive_prompt(prompt_str, prompt_str, clean_model_name)

    if provider == "openai":
        return openai_llm.text_prompt(prompt_str, model_name)
    elif provider == "ollama":
        return ollama_llm.text_prompt(prompt_str, model_name)
    elif provider == "anthropic":
        return anthropic_llm.text_prompt(prompt_str, model_name)
    elif provider == "gemini":
        return gemini_llm.text_prompt(prompt_str, model_name)
    elif provider == "deepseek":
        return deepseek_llm.text_prompt(prompt_str, model_name)
    else:
        raise ValueError(f"Unsupported provider: {provider}")


def tool_prompt(prompt: PromptWithToolCalls) -> ToolCallResponse:
    model_str = str(prompt.model)
    parts = model_str.split(":", 1)
    if len(parts) < 2:
        raise ValueError("No provider prefix found in model string")
    provider = parts[0]
    model_name = parts[1]

    if provider == "openai":
        return openai_llm.tool_prompt(prompt.prompt, model_name, all_tools_list)
    elif provider == "anthropic":
        return anthropic_llm.tool_prompt(prompt.prompt, model_name)
    elif provider == "gemini":
        return gemini_llm.tool_prompt(prompt.prompt, model_name, all_tools_list)
    elif provider == "deepseek":
        raise ValueError("DeepSeek does not support tool calls")
    elif provider == "ollama":
        raise ValueError("Ollama does not support tool calls")
    else:
        raise ValueError(f"Unsupported provider for tool calls: {provider}")

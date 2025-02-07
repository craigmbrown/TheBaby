from ollama import chat
from modules.data_types import PromptResponse, BenchPromptResponse
from utils import timeit
import json


def text_prompt(prompt: str, model: str) -> PromptResponse:
    """
    Send a prompt to Ollama and get a response.
    """
    try:
        with timeit() as t:
            response = chat(
                model=model,
                messages=[
                    {
                        "role": "user",
                        "content": prompt,
                    },
                ],
            )
            elapsed_ms = t()

        return PromptResponse(
            response=response.message.content,
            runTimeMs=elapsed_ms,  # Now using actual timing
            inputAndOutputCost=0.0,  # Ollama is free
        )
    except Exception as e:
        print(f"Ollama error: {str(e)}")
        return PromptResponse(
            response=f"Error: {str(e)}", runTimeMs=0, inputAndOutputCost=0.0
        )


def get_ollama_costs() -> tuple[int, int]:
    """
    Return token costs for Ollama (always 0 since it's free)
    """
    return 0, 0


def bench_prompt(prompt: str, model: str) -> BenchPromptResponse:
    """
    Send a prompt to Ollama and get detailed benchmarking response.
    """
    try:
        response = chat(
            model=model,
            messages=[
                {
                    "role": "user",
                    "content": prompt,
                },
            ],
        )

        # Calculate tokens per second using eval_count and eval_duration
        eval_count = response.get("eval_count", 0)
        eval_duration_ns = response.get("eval_duration", 0)

        # Convert nanoseconds to seconds and calculate tokens per second
        eval_duration_s = eval_duration_ns / 1_000_000_000
        tokens_per_second = eval_count / eval_duration_s if eval_duration_s > 0 else 0

        # Create BenchPromptResponse
        bench_response = BenchPromptResponse(
            response=response.message.content,
            tokens_per_second=tokens_per_second,
            provider="ollama",
            total_duration_ms=response.get("total_duration", 0)
            / 1_000_000,  # Convert ns to ms
            load_duration_ms=response.get("load_duration", 0)
            / 1_000_000,  # Convert ns to ms
        )

        # print(json.dumps(bench_response.dict(), indent=2))

        return bench_response

    except Exception as e:
        print(f"Ollama error: {str(e)}")
        return BenchPromptResponse(
            response=f"Error: {str(e)}",
            tokens_per_second=0.0,
            provider="ollama",
            total_duration_ms=0.0,
            load_duration_ms=0.0,
            errored=True,
        )

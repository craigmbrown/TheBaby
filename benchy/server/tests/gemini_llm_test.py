import pytest
from modules.gemini_llm import text_prompt

def test_gemini_text_prompt():
    response = text_prompt("ping", "gemini-1.5-pro-002")
    assert response.response != ""
    assert response.runTimeMs > 0
    assert response.inputAndOutputCost > 0.0

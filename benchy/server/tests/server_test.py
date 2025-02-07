import pytest
from server import app
from modules.data_types import ModelAlias


@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


@pytest.mark.parametrize(
    "model",
    [
        ModelAlias.haiku,
        ModelAlias.sonnet,
        ModelAlias.gemini_pro_2,
        ModelAlias.gemini_flash_2,
        ModelAlias.gemini_flash_8b,
        ModelAlias.gpt_4o_mini,
        ModelAlias.gpt_4o,
        ModelAlias.gpt_4o_predictive,
    ],
)
def test_prompt(client, model):
    response = client.post("/prompt", json={"prompt": "ping", "model": model})
    assert response.status_code == 200
    data = response.get_json()
    assert isinstance(data["response"], str)
    assert isinstance(data["runTimeMs"], int)
    assert isinstance(data["inputAndOutputCost"], (int, float))
    assert data["runTimeMs"] > 0
    assert data["inputAndOutputCost"] >= 0


@pytest.mark.parametrize(
    "prompt,expected_tool_calls,model",
    [
        (
            "Write code in main.py. Next, git commit that change.",
            ["run_coder_agent", "run_git_agent"],
            ModelAlias.gpt_4o,
        ),
        ("Write some code", ["run_coder_agent"], ModelAlias.gpt_4o_mini),
        ("Document this feature", ["run_docs_agent"], ModelAlias.gpt_4o),
    ],
)
def test_tool_prompt(client, prompt, expected_tool_calls, model):
    response = client.post(
        "/tool-prompt",
        json={
            "prompt": prompt,
            "expected_tool_calls": expected_tool_calls,
            "model": model,
        },
    )

    assert response.status_code == 200
    data = response.get_json()

    # Verify response structure
    assert "tool_calls" in data
    assert "runTimeMs" in data
    assert "inputAndOutputCost" in data

    # Verify tool calls
    assert isinstance(data["tool_calls"], list)
    assert len(data["tool_calls"]) == len(expected_tool_calls)

    # Verify each tool call
    for tool_call in data["tool_calls"]:
        assert isinstance(tool_call, dict)
        assert "tool_name" in tool_call
        assert "params" in tool_call
        assert tool_call["tool_name"] in expected_tool_calls
        assert isinstance(tool_call["params"], dict)
        assert len(tool_call["params"]) > 0

    # Verify timing and cost
    assert isinstance(data["runTimeMs"], int)
    assert isinstance(data["inputAndOutputCost"], (int, float))
    assert data["runTimeMs"] > 0
    assert data["inputAndOutputCost"] >= 0

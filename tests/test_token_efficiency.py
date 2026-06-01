"""Test agent loop with a scripted fake LLM (no network needed).

Verifies the multi-turn message construction end-to-end:
- system_prompt is sent on every call (so OpenAI/Groq can cache the prefix)
- messages grows incrementally, NOT by re-sending the full history as
  a single concatenated user string
- Early-break kicks in on 'Final Answer:'
- _compact_observation is applied to tool outputs
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.agent.agent import ReActAgent
from src.tools.travel_tools import ALL_TOOLS


class FakeLLM:
    """Scripted LLM that returns pre-canned responses and records every call."""

    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []  # list of (messages, system_prompt, stop)

    @property
    def model_name(self):
        return "fake-model"

    def generate(self, messages=None, system_prompt=None, stop=None,
                 prompt=None, **_):
        self.calls.append({
            "messages": [dict(m) for m in (messages or [])],
            "system_prompt_len": len(system_prompt or ""),
            "stop": stop,
        })
        # Pop next scripted response.
        content = self.responses.pop(0)
        return {
            "content": content,
            "usage": {"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150},
            "latency_ms": 1,
            "provider": "fake",
        }


def test_full_flow_compact_observations():
    # 1) weather, 2) flights+hotel parallel, 3) total price, 4) Final Answer
    scripted = [
        # step 0
        "Thought: Kiểm tra thời tiết trước.\n"
        "Action: get_weather(\"Đà Nẵng\", \"2025-06-20\")",
        # step 1
        "Thought: Tìm flight + hotel song song.\n"
        "Action: search_flights(\"Hà Nội\", \"Đà Nẵng\", \"2025-06-20\")\n"
        "Action: hotel(\"Đà Nẵng\", \"mid\")",
        # step 2
        "Thought: Tính tổng.\n"
        "Action: calculate_total_price(\"VJ456\", \"HTL_012\")",
        # step 3 (final)
        "Final Answer: Đà Nẵng 34°C mưa 80%. VJ456+HTL_012 = 1,400,000đ.",
    ]
    llm = FakeLLM(scripted)
    agent = ReActAgent(llm=llm, tools=ALL_TOOLS, max_steps=5)
    ans = agent.run("Tìm chuyến đi Đà Nẵng từ Hà Nội ngày 2025-06-20, tầm trung, budget 2tr")

    # Early-break: should stop at step 3 (the "Final Answer" turn).
    assert len(llm.calls) == 4, f"expected 4 LLM calls, got {len(llm.calls)}"

    # First call: just the user message
    c0 = llm.calls[0]
    assert len(c0["messages"]) == 1
    assert c0["messages"][0]["role"] == "user"
    # System prompt is sent (so OpenAI can cache the prefix)
    assert c0["system_prompt_len"] > 0

    # Second call: user + assistant + user(observation). The OBSERVATION must
    # be compact (top-3 projection).
    c1 = llm.calls[1]
    assert len(c1["messages"]) == 3
    obs_msg = c1["messages"][2]["content"]
    assert obs_msg.startswith("Observation:")
    # weather dict has 2 keys, not a list of dicts -> no projection
    assert "rain_prob" in obs_msg or "temp" in obs_msg
    # stop sequences should be configured
    assert "Observation:" in c1["stop"]

    # Third call: messages should be 5 entries (2 tool obs merged into 1 user msg
    # per turn, then assistant, then observation for the total call).
    c2 = llm.calls[2]
    # We send assistant turn + 1 observation turn each step, so:
    # turn 0: [user0]
    # turn 1: [user0, asst1, user(obs1)]
    # turn 2: [user0, asst1, user(obs1), asst2, user(obs2)]
    assert len(c2["messages"]) == 5
    obs2 = c2["messages"][4]["content"]
    # observation from calculate_total_price (dict, not list of dicts)
    assert "Observation:" in obs2

    # Fourth call is the Final Answer turn.
    c3 = llm.calls[3]
    assert len(c3["messages"]) == 7

    # The extracted final answer must NOT contain Action/Observation/Thought lines.
    assert "Action:" not in ans
    assert "Thought:" not in ans
    assert "Đà Nẵng" in ans and "VJ456" in ans

    print("OK: full flow with compact observations + early-break.")


def test_token_growth_is_linear_not_quadratic():
    """The OLD design concatenated everything into one user string, so
    prompt_tokens grew ~O(n^2). The NEW design sends a messages array, so
    the per-call prompt size should grow ~linearly (each new turn adds a
    small delta, not the entire history)."""
    scripted = [
        "Thought: bước 1.\nAction: get_weather(\"Đà Nẵng\", \"2025-06-20\")",
        "Thought: bước 2.\nAction: get_weather(\"Hà Nội\", \"2025-06-20\")",
        "Thought: bước 3.\nAction: get_weather(\"Sài Gòn\", \"2025-06-20\")",
        "Final Answer: xong.",
    ]
    llm = FakeLLM(scripted)
    agent = ReActAgent(llm=llm, tools=ALL_TOOLS, max_steps=5)
    agent.run("test")

    # The size of `messages` per call should grow by a small constant each turn
    # (assistant + observation = 2 new entries per step), NOT by the full
    # accumulated history.
    sizes = [len(c["messages"]) for c in llm.calls]
    assert sizes == [1, 3, 5, 7], f"expected linear growth 1,3,5,7 — got {sizes}"
    print(f"OK: message-array size per call = {sizes} (linear, not O(n^2)).")


def test_early_break_on_final_answer():
    scripted = [
        # Model skips all tools and just answers directly.
        "Final Answer: Tôi cần bạn cho biết phân khúc khách sạn (budget/mid/luxury).",
    ]
    llm = FakeLLM(scripted)
    agent = ReActAgent(llm=llm, tools=ALL_TOOLS, max_steps=5)
    ans = agent.run("Tìm chuyến đi Đà Nẵng ngày 2025-06-20")

    # Only one LLM call should have been made.
    assert len(llm.calls) == 1
    assert "phân khúc" in ans
    print("OK: early break after Final Answer (1 call instead of max_steps=5).")


def test_compact_observation_top3():
    """A tool returning a list of 5 flights should be compacted to at most
    3 'id:price' entries."""
    from src.agent.agent import _compact_observation

    long_list = [
        {"flight_id": f"VJ{i}", "price": 100000 + i} for i in range(5)
    ]
    out = _compact_observation(long_list)
    # Should contain 3 entries, not 5.
    assert out.count(":") == 3, f"expected 3 entries, got: {out}"
    assert "VJ0" in out and "VJ2" in out and "VJ4" not in out
    print(f"OK: compact observation = {out}")


if __name__ == "__main__":
    test_full_flow_compact_observations()
    test_token_growth_is_linear_not_quadratic()
    test_early_break_on_final_answer()
    test_compact_observation_top3()
    print("\nALL TESTS PASSED ✅")

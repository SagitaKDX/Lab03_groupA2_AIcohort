import sys, os, json
from datetime import datetime, timezone

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from src.core.llm_provider import get_provider

SYSTEM = "You are a helpful travel assistant. Answer the user's question as best you can."

def _log(event: str, payload: dict):
    print(f"LOG_EVENT: {event} {json.dumps({**payload, 'ts': datetime.now(timezone.utc).isoformat()})}")


def run_chatbot(query: str, provider_name: str | None = None) -> str:
    provider = get_provider(provider_name)

    result = provider.generate(prompt=query, system_prompt=SYSTEM)

    usage   = result["usage"]
    latency = result["latency_ms"]
    content = result["content"]

    _log("LLM_METRIC", {
        "mode": "chatbot",
        "provider": result.get("provider"),
        "prompt_tokens": usage["prompt_tokens"],
        "completion_tokens": usage["completion_tokens"],
        "total_tokens": usage["total_tokens"],
        "latency_ms": latency,
    })

    print(
        f"[chatbot] provider={result.get('provider')} | "
        f"tokens={usage['prompt_tokens']}+{usage['completion_tokens']} | "
        f"latency={latency}ms"
    )
    return content


if __name__ == "__main__":
    query =(
            "I want to fly from Hanoi to Tokyo on 2025-09-15, stay 3 nights at a 4-star hotel. "
            "Check the weather, find the cheapest flight, and calculate the total cost with 10% tax."
        ),


    for q in query:
        print(f"\n{'='*60}\nQUERY: {q}\n{'─'*60}")
        print(run_chatbot(q))
        print()
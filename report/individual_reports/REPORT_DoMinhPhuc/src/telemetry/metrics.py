from typing import Dict, Any, List
from src.telemetry.logger import logger

# ── Real per-model pricing (USD per 1M tokens, as of mid-2025) ───────────────
_PRICING = {
    # model substring → (input_price_per_1M, output_price_per_1M)
    "gpt-4o":            (5.00,  15.00),
    "gpt-4o-mini":       (0.15,   0.60),
    "gpt-4-turbo":      (10.00,  30.00),
    "gpt-3.5":           (0.50,   1.50),
    "gemini-1.5-flash":  (0.075,  0.30),
    "gemini-1.5-pro":    (3.50,  10.50),
    "gemini-2.0-flash":  (0.10,   0.40),
}
_DEFAULT_PRICE = (1.00, 3.00)   # safe fallback for unknown models


class PerformanceTracker:
    """
    Industry-standard metrics tracker for LLM sessions.
    Tracks per-request and session-aggregate stats, writes to telemetry logger.
    """
    def __init__(self):
        self.session_metrics: List[Dict[str, Any]] = []

    # ── Per-request tracking ──────────────────────────────────────────────────

    def track_request(self, provider: str, model: str, usage: Dict[str, int], latency_ms: int):
        """Call once per LLM response. Logs to file + console via IndustryLogger."""
        prompt_tokens      = usage.get("prompt_tokens", 0)
        completion_tokens  = usage.get("completion_tokens", 0)
        total_tokens       = usage.get("total_tokens", 0)
        cost               = self._calculate_cost(model, usage)

        # Token efficiency ratio: how much of the total was output vs input?
        # High ratio = model is "chatty"; low ratio = concise completions.
        efficiency_ratio = (
            round(completion_tokens / prompt_tokens, 3) if prompt_tokens else 0
        )

        metric = {
            "provider":         provider,
            "model":            model,
            "prompt_tokens":    prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens":     total_tokens,
            "latency_ms":       latency_ms,
            "cost_usd":         cost,
            "token_ratio":      efficiency_ratio,   # completion / prompt
        }

        self.session_metrics.append(metric)
        logger.log_event("LLM_METRIC", metric)
        return metric

    # ── Session-level aggregates ──────────────────────────────────────────────

    def session_summary(self) -> Dict[str, Any]:
        """Call at the end of an agent run to get aggregate stats."""
        if not self.session_metrics:
            return {}

        total_prompt      = sum(m["prompt_tokens"]     for m in self.session_metrics)
        total_completion  = sum(m["completion_tokens"] for m in self.session_metrics)
        total_tokens      = sum(m["total_tokens"]      for m in self.session_metrics)
        total_cost        = sum(m["cost_usd"]          for m in self.session_metrics)
        avg_latency       = sum(m["latency_ms"]        for m in self.session_metrics) / len(self.session_metrics)

        summary = {
            "steps":              len(self.session_metrics),
            "total_prompt_tokens":     total_prompt,
            "total_completion_tokens": total_completion,
            "total_tokens":            total_tokens,
            "total_cost_usd":          round(total_cost, 6),
            "avg_latency_ms":          round(avg_latency, 1),
            "overall_token_ratio":     round(total_completion / total_prompt, 3) if total_prompt else 0,
        }

        logger.log_event("SESSION_SUMMARY", summary)
        return summary

    # ── Pricing ───────────────────────────────────────────────────────────────

    def _calculate_cost(self, model: str, usage: Dict[str, int]) -> float:
        """Real per-model cost estimate based on input/output token pricing."""
        model_lower = model.lower()
        input_price, output_price = _DEFAULT_PRICE
        for key, prices in _PRICING.items():
            if key in model_lower:
                input_price, output_price = prices
                break

        input_cost  = (usage.get("prompt_tokens",     0) / 1_000_000) * input_price
        output_cost = (usage.get("completion_tokens", 0) / 1_000_000) * output_price
        return round(input_cost + output_cost, 8)


# Global tracker instance
tracker = PerformanceTracker()
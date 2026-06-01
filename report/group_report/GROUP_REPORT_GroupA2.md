# Group Report: Lab 3 - Production-Grade Agentic System

- **Team Name**: Group A2
- **Team Members**: Đỗ Minh Phúc (Student ID: 2A202600585), Nguyen Văn Minh (Student ID: 2A202600904), Phí Đình Mạnh (Student ID: 2A202600826), Nguyễn Lê Thanh Điệp (Student ID: 2A202600636), Lê Thanh Minh (Student ID: 2A202600972)
- **Deployment Date**: 2026-06-01

---

## 1. Executive Summary

- **Success Rate**: 83.3% (5 out of 6 test sessions completed successfully; 1 session failed/crashed due to the Gemini provider safety blockage, which has since been resolved and patched).
- **Key Outcome**: The ReAct Agent correctly resolved complex multi-step queries (such as checking visa rules, searching flights/hotels, and calculating total cost with currency conversions) by utilizing grounded tools in a 7-step sequence. In contrast, the baseline chatbot failed completely on these multi-step queries, hallucinating prices and visa policies from its pre-training weights, or refusing to answer due to a lack of real-time data.

---

## 2. System Architecture & Tooling

### 2.1 ReAct Loop Implementation
We implemented the `Thought-Action-Observation` cycle in [`src/agent/agent.py`](https://github.com/SagitaKDX/Lab03_groupA2_AIcohort/blob/main/src/agent/agent.py). The agent generates a `Thought` identifying what to do, formats an `Action: tool_name(args)` to execute, yields execution control to the system backend, receives the tool's output as an `Observation` formatted from the CSV database, and continues iteratively until it outputs `Final Answer: ...`.

### 2.2 Tool Definitions (Inventory)
| Tool Name | Input Format | Use Case |
| :--- | :--- | :--- |
| `check_visa_requirements` | `passport_nationality: str, destination_country: str` | Verify visa requirements and notes for a specific passport holder. |
| `get_weather` | `destination_city: str, departure_date: str` | Check weather temperature (C) and rain probability. |
| `search_flights` | `departure_city: str, destination_city: str, departure_date: str` | Search flight options and prices (in USD). |
| `search_hotels` | `destination_city: str, rate: int` | Search hotel price per night (in USD) based on star rating. |
| `calculate_total_price` | `flight_id: str, hotel_id: str` | Calculate total trip cost (flight + 3 nights hotel). |
| `convert_currency` | `base_currency: str, target_currency: str, amount: float` | Convert base currency to target currency using exchange rates. |
| `get_current_time` | `timezone: str` | Retrieve current date and time in the specified timezone. |

### 2.3 LLM Providers Used
- **Primary**: OpenAI (`gpt-4o`)
- **Secondary (Backup)**: Google Gemini (`gemini-3.5-flash` / `gemini-2.5-flash`)
- **Local Model**: Microsoft (`Phi-3-mini-4k-instruct-q4.gguf`) run locally on CPU via `llama-cpp-python`.

---

## 3. Telemetry & Performance Dashboard

- **Average Latency (P50)**: 1847.0 ms
- **Max Latency (P99)**: 9901.7 ms
- **Average Tokens per Session**: 4974.6 tokens
- **Total Cost of Test Suite**: $0.09 USD (estimated for GPT-4o and Gemini usage)

---

## 4. Root Cause Analysis (RCA) - Failure Traces

### 4.1 Case Study 1: Parsing Failure with Local Model (Phi-3)
- **Input**: "convert 100 usd to vnd"
- **Observation**: At Step 2, the local model generated a conversational sentence instead of the prefix `Final Answer:` or `Action:`:
  `You have converted 100 USD to VND using the current exchange rate of 25,400.0. Here's the converted amount: 100 USD = 2,540,000 VND...`
- **Root Cause**: Small GGUF models are prone to format drift, losing track of strict stop sequences and attempting to chat or write explanation sentences rather than adhering to raw ReAct syntax.
- **Solution**: We added strong few-shot examples showing exactly when to yield control and when to print `Final Answer:`, and robustified the backend parser to fall back if the model outputs a valid tool call structure even if the `Action:` prefix is omitted.

### 4.2 Case Study 2: Provider Blockage Crash (Gemini 2.5 Flash)
- **Input**: "convert 100 usd to vnd"
- **Observation**: The Gemini API returned `finish_reason` 12, causing the `response.text` quick accessor to raise a `ValueError` (no parts returned), crashing the entire server with a 500 code.
- **Root Cause**: The API key triggered safety/quota blocklist filters (value 12 is an undocumented safety/blocked code). The baseline provider wrapper lacked exception handling around candidate extraction and usage metadata.
- **Solution**: Wrapped the content extraction and usage metadata parsing in try-except blocks, mapping blocked codes (like FinishReason 12) to clean text warnings and 0 token usages, allowing the ReAct loop to fail gracefully instead of crashing.

### 4.3 Deep Critical Analysis: Why Agentic Systems Fail
Through empirical testing in this lab, we identified four fundamental failure vectors inherent in LLM-based ReAct agents:
1. **Parser Drift and Syntax Sensitivity**: The agent's control flow relies entirely on regex pattern matching of `Thought:`, `Action:`, and `Final Answer:`. Smaller models or poorly-prompted online models often generate markdown formatting (e.g. `Action: ```python\n...``` `) or wrap actions in conversational text. If the regex parser fails to match these patterns, the loop breaks or throws formatting observations back to the LLM, leading to reasoning degradation.
2. **Cascading Failure Loop (Infinite Execution)**: When a tool returns an unexpected output (e.g., an error message or empty JSON `{}`), the LLM often struggles to parse the failure. Instead of adjusting its parameters, it repeatedly invokes the same tool with identical invalid parameters (e.g., calling `search_flights` with a missing date), entering an infinite execution loop until terminated by `max_steps`.
3. **Context Space Saturation**: In multi-step loops, feeding back large raw tool outputs (e.g., raw search observations or long API outputs) consumes context space rapidly. Because prompt history is re-sent in every turn, large observations bloat the context window, dilute the system instruction weights, and trigger reasoning drift.
4. **Unhandled SDK and API Provider Exceptions**: Cloud model providers have strict safety, input-size, and quota limit filters. When these are triggered (such as Gemini's undocumented FinishReason 12 safety flag), the SDK raises internal errors (like `ValueError` for empty candidates). Lacking defensive wrappers in the provider layer causes the entire runtime server to crash.

---

## 5. Ablation Studies & Experiments

### Experiment 1: Prompt v1 (Few-Shot) vs Prompt v2 (No Few-Shot)
- **Diff**: Removing the few-shot example traces from the system instructions.
- **Result**: On cloud models (GPT-4o), success rate remained stable but occasionally missed step chaining. On the local model (Phi-3-mini), format compliance dropped from **90% down to 30%**, showing that few-shot examples are critical for guiding smaller models to follow syntax rules.

### Experiment 2: Chatbot vs Agent
| Case | Chatbot Result | Agent Result | Winner |
| :--- | :--- | :--- | :--- |
| Simple Q | Correct | Correct | Draw |
| Multi-step | Hallucinated | Correct | **Agent** |

### 5.1 Deep Critical Analysis: Impact of Missing Prompt Guardrails
When prompt constraints, strict formatting templates, or few-shot examples are omitted (as in `prompt_without_fewshot` or `no_prompt` modes), the agent's performance collapses due to the following factors:
1. **Loss of Yield Compliance (Self-Observation Generation)**: Without explicit few-shot traces indicating where the model must stop generating text, small models fail to yield control. Instead of stopping after writing `Action: tool(...)`, the model generates the `Observation:` block itself, inventing mock tool responses and closing the loop on a hallucinated trajectory without ever hitting the actual database.
2. **Context Growth O(N^2)**: Missing explicit instruction guardrails leads to verbose, conversational explanations during intermediate steps. Instead of outputting single-line thoughts and concise actions, the model writes paragraphs. This increases token consumption quadratically with each turn, raising operational cost and slowing latency.
3. **Reasoning Drift**: Without strict rules enforcing sequential step dependency (e.g., "Check visa rules before booking flights"), the LLM tries to guess or skip steps (e.g., calling `calculate_total_price` with placeholder/hallucinated IDs), losing its analytical grounding.

---

## 6. Production Readiness Review

- **Security**: Sanitized input strings passed to the tool executor using strict regex constraints to prevent code injection via python `eval` or command injection.
- **Guardrails**: Added a hard step timeout (`max_steps=10`) in `src/agent/agent.py` to prevent infinite loops and limit billing costs.
- **Scaling**: Proposed transitioning to asynchronous parallel tool runs and using LangGraph to implement structured routing state machines for complex multi-turn sub-agents.

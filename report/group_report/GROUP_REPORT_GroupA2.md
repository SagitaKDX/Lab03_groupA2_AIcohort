# Group Report: Lab 3 - Production-Grade Agentic System

- **Team Name**: Group A2
- **Team Members**: Lê Thanh Minh (Student ID: 2A02600872), Nguyen Van Minh, phimanh
- **Deployment Date**: 2026-06-01

---

## 1. Executive Summary

*Brief overview of the agent's goal and success rate compared to the baseline chatbot.*

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

*Analyze the industry metrics collected during the final test run.*

- **Average Latency (P50)**: 1847.0 ms
- **Max Latency (P99)**: 9901.7 ms
- **Average Tokens per Session**: 4974.6 tokens
- **Total Cost of Test Suite**: $0.09 USD (estimated for GPT-4o and Gemini usage)

---

## 4. Root Cause Analysis (RCA) - Failure Traces

*Deep dive into why the agent failed.*

### Case Study 1: Parsing Failure with Local Model (Phi-3)
- **Input**: "convert 100 usd to vnd"
- **Observation**: At Step 2, the local model generated a conversational sentence instead of the prefix `Final Answer:` or `Action:`:
  `You have converted 100 USD to VND using the current exchange rate of 25,400.0. Here's the converted amount: 100 USD = 2,540,000 VND...`
- **Root Cause**: Small GGUF models are prone to format drift, losing track of strict stop sequences and attempting to chat or write explanation sentences rather than adhering to raw ReAct syntax.
- **Solution**: We added strong few-shot examples showing exactly when to yield control and when to print `Final Answer:`, and robustified the backend parser to fall back if the model outputs a valid tool call structure even if the `Action:` prefix is omitted.

### Case Study 2: Provider Blockage Crash (Gemini 2.5 Flash)
- **Input**: "convert 100 usd to vnd"
- **Observation**: The Gemini API returned `finish_reason` 12, causing the `response.text` quick accessor to raise a `ValueError` (no parts returned), crashing the entire server with a 500 code.
- **Root Cause**: The API key triggered safety/quota blocklist filters (value 12 is an undocumented safety/blocked code). The baseline provider wrapper lacked exception handling around candidate extraction and usage metadata.
- **Solution**: Wrapped the content extraction and usage metadata parsing in try-except blocks, mapping blocked codes (like FinishReason 12) to clean text warnings and 0 token usages, allowing the ReAct loop to fail gracefully instead of crashing.

---

## 5. Ablation Studies & Experiments

### Experiment 1: Prompt v1 (Few-Shot) vs Prompt v2 (No Few-Shot)
- **Diff**: Removing the few-shot example traces from the system instructions.
- **Result**: On cloud models (GPT-4o), success rate remained stable but occasionally missed step chaining. On the local model (Phi-3-mini), format compliance dropped from **90% down to 30%**, showing that few-shot examples are critical for guiding smaller models to follow syntax rules.

### Experiment 2 (Bonus): Chatbot vs Agent
| Case | Chatbot Result | Agent Result | Winner |
| :--- | :--- | :--- | :--- |
| Simple Q | Correct | Correct | Draw |
| Multi-step | Hallucinated | Correct | **Agent** |

---

## 6. Production Readiness Review

*Considerations for taking this system to a real-world environment.*

- **Security**: Sanitized input strings passed to the tool executor using strict regex constraints to prevent code injection via python `eval` or command injection.
- **Guardrails**: Added a hard step timeout (`max_steps=10`) in `src/agent/agent.py` to prevent infinite loops and limit billing costs.
- **Scaling**: Proposed transitioning to asynchronous parallel tool runs and using LangGraph to implement structured routing state machines for complex multi-turn sub-agents.

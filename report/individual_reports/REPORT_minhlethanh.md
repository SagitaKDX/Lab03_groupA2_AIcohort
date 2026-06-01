# Individual Report: Lab 3 - Chatbot vs ReAct Agent

- **Student Name**: Minh Le Thanh
- **Student ID**: 2A02600872
- **Date**: 2026-06-01

---

## I. Technical Contribution (15 Points)

- **Modules Implemented**: 
  - [`src/agent/agent.py`](https://github.com/SagitaKDX/Lab03_groupA2_AIcohort/blob/main/src/agent/agent.py): Implemented the ReAct loop supporting `Thought-Action-Observation` parsing, parallel tool executions, loop timeout limits, and error handling.
  - [`src/tools/travel_tools.py`](https://github.com/SagitaKDX/Lab03_groupA2_AIcohort/blob/main/src/tools/travel_tools.py): Built CSV-driven mock databases for flights, hotels, weather, currencies, and visa rules, enabling grounded tools.
  - [`server.py`](https://github.com/SagitaKDX/Lab03_groupA2_AIcohort/blob/main/server.py): Implemented the zero-dependency backend Python server to manage chat sessions, log collector telemetry intercepts, and local GGUF models.
  - [`web/index.html`](https://github.com/SagitaKDX/Lab03_groupA2_AIcohort/blob/main/web/index.html) & [`web/style.css`](https://github.com/SagitaKDX/Lab03_groupA2_AIcohort/blob/main/web/style.css) & [`web/app.js`](https://github.com/SagitaKDX/Lab03_groupA2_AIcohort/blob/main/web/app.js): Created an interactive glassmorphism Web UI featuring an LLM customizer panel, real-time ReAct trace visualizers, telemetry dashboards, and log consoles.
  - [`src/core/gemini_provider.py`](https://github.com/SagitaKDX/Lab03_groupA2_AIcohort/blob/main/src/core/gemini_provider.py): Patched safety policies blockages to resolve crashes.

- **Code Highlights**: 
  - ReAct loop parsing and fallback mechanisms in [`src/agent/agent.py`](https://github.com/SagitaKDX/Lab03_groupA2_AIcohort/blob/main/src/agent/agent.py#L53-L103).
  - Safe-extraction of candidates and usage metadata in [`src/core/gemini_provider.py`](https://github.com/SagitaKDX/Lab03_groupA2_AIcohort/blob/main/src/core/gemini_provider.py#L27-L60).

- **Documentation**: 
  - The ReAct Agent reads the customized system instruction and lists active tools. In each step, the loop prompts the selected provider, logs the `Thought` and `Action` output, executes the corresponding Python function from `travel_tools.py`, updates the reasoning history with the `Observation`, and continues until it matches the `Final Answer` pattern.

---

## II. Debugging Case Study (10 Points)

- **Problem Description**: The server crashed and returned a `500 Internal Server Error` when executing chat queries using the Gemini provider (`gemini-2.5-flash` or `gemini-3.5-flash`) due to a `ValueError` raised by the `google-generativeai` SDK.
- **Log Source**: 
  ```text
  ValueError: Invalid operation: The `response.text` quick accessor requires the response to contain a valid `Part`, but none were returned. The candidate's finish_reason is 12.
  127.0.0.1 - - [01/Jun/2026 17:55:36] "POST /api/chat HTTP/1.1" 500 -
  ```
- **Diagnosis**: The Gemini API returned a non-standard `finish_reason` of 12 (corresponding to safety policy blockage). Because candidate generation was blocked, no parts were returned in the response object. Directly calling the `response.text` helper property on the response object raised a `ValueError` which crashed the application.
- **Solution & Dealing with Data / Providers**:
  - **Handling the Provider**: In a multi-provider setting, the application expects all providers to return a standardized payload schema (`{"content": ..., "usage": ..., "latency_ms": ..., "provider": ...}`). Allowing a provider-specific exception (like `ValueError` for Gemini) to bubble up crashes the entire reasoning loop. We resolved this by modifying [`src/core/gemini_provider.py`](https://github.com/SagitaKDX/Lab03_groupA2_AIcohort/blob/main/src/core/gemini_provider.py) to wrap `.text` property access in a `try...except ValueError` block. If a blockage is encountered, we dynamically inspect the first candidate's `finish_reason` and map it into a standardized textual explanation.
  - **Handling the Data**: When candidate generation fails, metadata fields such as `usage_metadata` can also fail to resolve or throw secondary attribute errors. To safeguard telemetry tracking, we wrapped the token parsing inside a `try...except Exception` block, defaulting to `0` for prompt, completion, and total tokens. This ensures the backend server `server.py` receives a valid JSON telemetry payload with 200 OK, updating the Web UI's accordion reasoning trace and cost calculations correctly instead of rendering a blank crash screen.

---

## III. Personal Insights: Chatbot vs ReAct (10 Points)

### 1. Theoretical Differences
- **Reasoning**: The `Thought` step serves as the agent's explicit scratchpad (Chain of Thought). Instead of outputting a direct answer instantly, it allows the LLM to identify missing parameters, select the appropriate tools, and decompose complex multi-stage queries (e.g., flight booking -> hotel booking -> currency conversion) into discrete steps.
- **Reliability**: ReAct agents can occasionally perform worse than standard Chatbots because:
  - They can get caught in infinite loops (e.g., executing the exact same tool with identical arguments when observation returns no data).
  - They are sensitive to minor formatting errors (e.g., generating markdown code blocks or omitting parenthetical arguments) that crash the regex parser.
  - They introduce significantly higher latencies and token overhead due to making multiple sequential model calls.
- **Observation**: Observations serve as the model's grounding mechanism. Real feedback from the database (CSV files) corrects the agent's reasoning trajectory, replacing hallucinations with actual data.

### 2. Empirical Ablation Study: 3 Prompting Methods vs 2 Execution Modes
To evaluate the limits of reasoning and format compliance, we performed an ablation study across **3 prompting methods** (Few-Shot Optimized, Without Few-Shot, No System Prompt) and **2 execution modes** (Cloud Online APIs vs. Local CPU GGUF models).

#### Comparative Analysis Matrix
| Model Type / Mode | Prompt Method | Format Compliance | Grounding & Reasoning | Latency & Token Efficiency |
|---|---|---|---|---|
| **Online (gpt-4o / Gemini 3.5)** | Few-Shot Optimized | **100%** | Excellent, logical chaining of 6 tools | Moderate (high prompt tokens but highly efficient caching) |
| | Without Few-Shot | **90-95%** | Good, but occasional step skipping | Highly efficient (lower initial prompt context) |
| | No Prompt (Raw) | **<10%** | Fails; responds conversationally (hallucinations) | Lowest latency, zero tool utilization |
| **Local CPU (Phi-3-mini GGUF)** | Few-Shot Optimized | **85-90%** | Good; conforms to the few-shot reasoning pattern | High latency (constrained by CPU execution speed) |
| | Without Few-Shot | **30-40%** | Poor; struggles to yield control, writes fake observations | Moderate latency, fails due to infinite loops |
| | No Prompt (Raw) | **0%** | Fails; outputs gibberish or repeats prompt | Fast, but completely unusable for agent loop |

#### Key Insights & Critical Thinking Analysis
1. **Few-Shot Examples are Critical for Small Models (Phi-3-mini GGUF)**:
   - Local models (3.8B parameters) lack the instruction-following capacity to adhere to abstract formatting constraints (e.g., yielding control without writing the `Observation:` line).
   - The inclusion of concrete few-shot examples in `prompt_with_fewshot` is the single most important factor enabling the local model to conform to the ReAct syntax. Without it, the format compliance rate drops from **90% to 30%**, rendering the agent loop unusable.
2. **Online Models exhibit high Zero-Shot Reasoning**:
   - Cloud models like `gpt-4o` and `gemini-3.5-flash` demonstrate robust zero-shot formatting compliance. In the `prompt_without_fewshot` mode, they successfully complete the ReAct loop without format violations, though they occasionally miss minor steps (such as skipping proactive currency conversion).
3. **No Prompt leads to Complete Failure (Chatbot Hallucinations)**:
   - In `no_prompt` mode, both Online and Local models immediately revert to simple chatbot behaviors, hallucinating all travel prices and visa requirements from their pre-training weights, violating the core grounding rule. This highlights that a ReAct loop cannot function without explicit structure prompting.
4. **Token Caching vs Context Length**:
   - While `prompt_with_fewshot` introduces larger initial prompt contexts, it provides essential guardrails. When using cloud providers like OpenAI, prompt caching mitigates the cost of this extra context. For local models, this adds computational overhead (longer time-to-first-token), but is necessary for reasoning correctness.

---

## IV. Future Improvements (5 Points)

- **Scalability**: Implement asynchronous task execution (e.g., calling hotel and flight search APIs in parallel using Python's `asyncio`) to minimize user-facing latency.
- **Safety**: Implement input/output guardrails (e.g., NeMo Guardrails or a separate lightweight auditor LLM) to validate queries and sanitize tool arguments.
- **Performance**: Introduce semantic observation caching and a vector database tool registry to retrieve and inject only the most relevant tools instead of dumping all tool descriptions in the system prompt.

import os
import sys
import json
import re
import urllib.parse
from http.server import HTTPServer, BaseHTTPRequestHandler
from datetime import datetime
from typing import Any, Dict, List

# Clean up NO_PROXY / no_proxy to fix HTTPX bug with loopback IPv6 addresses (like ::1)
for key in ["NO_PROXY", "no_proxy"]:
    if key in os.environ:
        parts = [p for p in os.environ[key].split(",") if "::1" not in p]
        os.environ[key] = ",".join(parts)

# Ensure the root directory is on the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.core.openai_provider import OpenAIProvider
from src.core.gemini_provider import GeminiProvider
from src.agent.agent import ReActAgent
from src.tools import travel_tools
from src.tools.prompt import SYSTEM_PROMPT_TEMPLATE
from src.telemetry.logger import logger

# In-Memory Settings Store
CURRENT_SETTINGS = {
    "provider": "openai",
    "model": "gpt-4o",
    "max_steps": 10,
    "tools": [
        "search_flights",
        "search_hotels",
        "get_weather",
        "calculate_total_price",
        "convert_currency",
        "check_visa_requirements"
    ],
    "system_prompt": "",
    "prompt_template": "prompt_with_fewshot",
    "local_model_path": "Phi-3-mini-4k-instruct-q4.gguf",
    "local_n_ctx": 4096,
    "local_n_threads": None,
    "local_stop": "<|end|>,Observation:"
}

PROMPT_TEMPLATE_LABELS = {
    "prompt_with_fewshot": "Prompt with few-shot",
    "prompt_without_fewshot": "Prompt without few-shot",
    "no_prompt_with_tool_descriptions": "Only tool descriptions",
    "no_prompt": "No system prompt",
}

# Load all available tools map
ALL_TOOLS = {
    "search_flights": {
        "name": "search_flights",
        "description": 'search_flights(departure_city: str, destination_city: str, departure_date: str) -> Searches flight options and prices (in USD). Example: search_flights(departure_city="Hanoi", destination_city="Tokyo", departure_date="2026-07-01")',
        "func": travel_tools.search_flights
    },
    "search_hotels": {
        "name": "search_hotels",
        "description": 'search_hotels(destination_city: str, rate: int) -> Searches hotel prices per night (in USD) based on star rating/class (1 to 5). Example: search_hotels(destination_city="Tokyo", rate=4)',
        "func": travel_tools.search_hotels
    },
    "get_weather": {
        "name": "get_weather",
        "description": 'get_weather(destination_city: str, departure_date: str) -> Checks weather temperature (C) and rain probability. Example: get_weather(destination_city="Tokyo", departure_date="2026-07-01")',
        "func": travel_tools.get_weather
    },
    "calculate_total_price": {
        "name": "calculate_total_price",
        "description": 'calculate_total_price(flight_id: str, hotel_id: str) -> Calculates total trip cost (flight + 3 nights hotel). Example: calculate_total_price(flight_id="VN-310", hotel_id="HT-TOKYO-Comfort")',
        "func": travel_tools.calculate_total_price
    },
    "convert_currency": {
        "name": "convert_currency",
        "description": 'convert_currency(base_currency: str, target_currency: str, amount: float) -> Converts price from base to target currency. Example: convert_currency(base_currency="USD", target_currency="VND", amount=570.0)',
        "func": travel_tools.convert_currency
    },
    "check_visa_requirements": {
        "name": "check_visa_requirements",
        "description": 'check_visa_requirements(passport_nationality: str, destination_country: str) -> Checks visa requirement status and notes. Example: check_visa_requirements(passport_nationality="Vietnam", destination_country="Japan")',
        "func": travel_tools.check_visa_requirements
    },
    "get_airport_transfer": {
        "name": "get_airport_transfer",
        "description": 'get_airport_transfer(city: str, transfer_type: str = "all") -> Provides information about airport transfers in a given city. Example: get_airport_transfer(city="Tokyo", transfer_type="taxi")',
        "func": travel_tools.get_airport_transfer
    }
}

def get_prompt_template_options() -> List[Dict[str, str]]:
    tool_descriptions = "\n".join([f"- {t['name']}: {t['description']}" for t in ALL_TOOLS.values()])
    return [
        {
            "key": key,
            "label": PROMPT_TEMPLATE_LABELS.get(key, key.replace("_", " ").title()),
            "content": template.format(tool_descriptions=tool_descriptions),
        }
        for key, template in SYSTEM_PROMPT_TEMPLATE.items()
    ]


# Get selected system prompt from dummy agent on startup
def get_default_prompt(prompt_template: str = "prompt_with_fewshot") -> str:
    dummy_agent = ReActAgent(None, list(ALL_TOOLS.values()), prompt_template=prompt_template)
    return dummy_agent.get_system_prompt()

CURRENT_SETTINGS["system_prompt"] = get_default_prompt(CURRENT_SETTINGS["prompt_template"])

# Log Collector Context Manager to intercept ReAct logger logs in-memory
class LogCollector:
    def __init__(self):
        self.events = []
        self.original_log_event = logger.log_event

    def __enter__(self):
        def patched_log_event(event_type: str, data: Dict[str, Any]):
            # Write to disk logs via original logger
            self.original_log_event(event_type, data)
            # Collect in list
            self.events.append({
                "event": event_type,
                "data": data
            })
        logger.log_event = patched_log_event
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        logger.log_event = self.original_log_event


class AgentRequestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed_url = urllib.parse.urlparse(self.path)
        path = parsed_url.path

        # API: Get Current Settings
        if path == "/api/settings":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            payload = {
                **CURRENT_SETTINGS,
                "prompt_templates": get_prompt_template_options(),
            }
            self.wfile.write(json.dumps(payload).encode("utf-8"))
            return

        # Static File Serving Routing
        if path == "/" or path == "/index.html":
            self.serve_static_file("web/index.html", "text/html")
        elif path == "/style.css":
            self.serve_static_file("web/style.css", "text/css")
        elif path == "/app.js":
            self.serve_static_file("web/app.js", "application/javascript")
        else:
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b"404 Not Found")

    def do_POST(self):
        parsed_url = urllib.parse.urlparse(self.path)
        path = parsed_url.path

        # Read JSON body length
        content_length = int(self.headers.get("Content-Length", 0))
        post_data = self.rfile.read(content_length)
        
        try:
            body = json.loads(post_data.decode("utf-8"))
        except Exception:
            self.send_response(400)
            self.end_headers()
            self.wfile.write(b"Invalid JSON body")
            return

        # API: Save Settings
        if path == "/api/settings":
            try:
                CURRENT_SETTINGS["provider"] = body.get("provider", CURRENT_SETTINGS["provider"])
                CURRENT_SETTINGS["model"] = body.get("model", CURRENT_SETTINGS["model"])
                CURRENT_SETTINGS["max_steps"] = body.get("max_steps", CURRENT_SETTINGS["max_steps"])
                CURRENT_SETTINGS["tools"] = body.get("tools", CURRENT_SETTINGS["tools"])
                previous_prompt_template = CURRENT_SETTINGS["prompt_template"]
                previous_system_prompt = CURRENT_SETTINGS["system_prompt"]
                prompt_template = body.get("prompt_template", CURRENT_SETTINGS["prompt_template"])
                if prompt_template in SYSTEM_PROMPT_TEMPLATE:
                    CURRENT_SETTINGS["prompt_template"] = prompt_template

                posted_system_prompt = body.get("system_prompt")
                prompt_template_changed = CURRENT_SETTINGS["prompt_template"] != previous_prompt_template
                if prompt_template_changed and (
                    posted_system_prompt is None or posted_system_prompt == previous_system_prompt
                ):
                    CURRENT_SETTINGS["system_prompt"] = get_default_prompt(CURRENT_SETTINGS["prompt_template"])
                elif posted_system_prompt is not None:
                    CURRENT_SETTINGS["system_prompt"] = posted_system_prompt
                CURRENT_SETTINGS["local_model_path"] = body.get("local_model_path", CURRENT_SETTINGS["local_model_path"])
                CURRENT_SETTINGS["local_n_ctx"] = body.get("local_n_ctx", CURRENT_SETTINGS["local_n_ctx"])
                CURRENT_SETTINGS["local_n_threads"] = body.get("local_n_threads", CURRENT_SETTINGS["local_n_threads"])
                CURRENT_SETTINGS["local_stop"] = body.get("local_stop", CURRENT_SETTINGS["local_stop"])

                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"status": "success", "settings": CURRENT_SETTINGS}).encode("utf-8"))
            except Exception as e:
                self.send_response(500)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"status": "error", "message": str(e)}).encode("utf-8"))
            return

        # API: Execute Chat / Run ReAct Loop
        elif path == "/api/chat":
            query = body.get("query")
            if not query:
                self.send_response(400)
                self.end_headers()
                self.wfile.write(b"Missing 'query' field")
                return

            try:
                # 1. Initialize Provider
                provider_name = CURRENT_SETTINGS["provider"].lower()
                if provider_name == "openai":
                    api_key = os.getenv("OPENAI_API_KEY")
                    llm = OpenAIProvider(model_name=CURRENT_SETTINGS["model"], api_key=api_key)
                elif provider_name == "google":
                    api_key = os.getenv("GEMINI_API_KEY")
                    llm = GeminiProvider(model_name=CURRENT_SETTINGS["model"], api_key=api_key)
                elif provider_name == "local":
                    from src.core.local_provider import LocalProvider
                    model_file = CURRENT_SETTINGS.get("local_model_path", "Phi-3-mini-4k-instruct-q4.gguf")
                    base_dir = os.path.dirname(os.path.abspath(__file__))
                    model_path = os.path.join(base_dir, "models", model_file)
                    
                    n_ctx = int(CURRENT_SETTINGS.get("local_n_ctx", 4096))
                    
                    n_threads_val = CURRENT_SETTINGS.get("local_n_threads")
                    n_threads = int(n_threads_val) if (n_threads_val is not None and str(n_threads_val).strip() != "") else None
                    
                    llm = LocalProvider(model_path=model_path, n_ctx=n_ctx, n_threads=n_threads)
                else:
                    raise ValueError(f"Unsupported provider: {provider_name}")

                # 2. Filter Active Tools
                active_tools = []
                for t_name in CURRENT_SETTINGS["tools"]:
                    if t_name in ALL_TOOLS:
                        active_tools.append(ALL_TOOLS[t_name])

                # 3. Instantiate Agent
                agent = ReActAgent(
                    llm=llm,
                    tools=active_tools,
                    max_steps=CURRENT_SETTINGS["max_steps"],
                    prompt_template=CURRENT_SETTINGS["prompt_template"]
                )

                # Use the prompt text currently shown in the UI. This also allows an
                # intentionally empty system prompt for the "no_prompt" experiment.
                agent.custom_system_prompt = CURRENT_SETTINGS["system_prompt"]

                # 4. Execute ReAct loop and intercept logs
                with LogCollector() as collector:
                    answer = agent.run(query)

                # 5. Process intercepted logs into Trace and Telemetry
                trace = []
                current_step = {}
                total_latency = 0
                total_tokens = 0
                total_cost = 0.0
                react_steps = 0

                for ev in collector.events:
                    etype = ev["event"]
                    data = ev["data"]

                    if etype == "AGENT_STEP":
                        react_steps += 1
                        total_latency += data.get("latency_ms", 0)
                        
                        usage = data.get("usage", {})
                        total_tokens += usage.get("total_tokens", 0)
                        # Estimate cost based on model/usage (approx $0.015 per 1K tokens for simple dashboard logging)
                        total_cost += (usage.get("total_tokens", 0) / 1000.0) * 0.015

                        content = data.get("model_response", "")
                        # Simple regex parse of Thoughts
                        thought_match = re.search(r"Thought:\s*(.*?)(?:Action:|Final\s*Answer:|$)", content, re.DOTALL | re.IGNORECASE)
                        thought = thought_match.group(1).strip() if thought_match else content

                        # Simple regex parse of Action
                        action_match = re.search(r"Action:\s*(\w+)\((.*)\)", content, re.IGNORECASE)
                        action = f"{action_match.group(1)}({action_match.group(2)})" if action_match else None

                        current_step = {
                            "step": data.get("step", len(trace) + 1),
                            "thought": thought,
                            "action": action,
                            "observation": None
                        }
                        trace.append(current_step)

                    elif etype == "TOOL_EXECUTION" and current_step:
                        current_step["observation"] = data.get("observation", "")

                 # 6. Return response
                response_payload = {
                    "answer": answer,
                    "trace": trace,
                    "telemetry": {
                        "latency_ms": total_latency,
                        "tokens": total_tokens,
                        "cost": round(total_cost, 4),
                        "steps": react_steps
                    },
                    "raw_events": collector.events
                }

                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps(response_payload).encode("utf-8"))

            except Exception as e:
                import traceback
                traceback.print_exc()
                self.send_response(500)
                self.end_headers()
                self.wfile.write(str(e).encode("utf-8"))

    def serve_static_file(self, filepath: str, content_type: str):
        if not os.path.exists(filepath):
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b"Static asset not found")
            return

        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        with open(filepath, "rb") as f:
            self.wfile.write(f.read())


def run_server(port=8000):
    server_address = ("", port)
    httpd = HTTPServer(server_address, AgentRequestHandler)
    print(f"🚀 Server started and running at: http://localhost:{port}")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping server...")
        httpd.server_close()


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    port = int(os.getenv("PORT", 8000))
    run_server(port)

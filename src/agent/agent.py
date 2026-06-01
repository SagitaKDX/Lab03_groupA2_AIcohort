import os
import re
import ast
from typing import List, Dict, Any, Optional
from src.core.llm_provider import LLMProvider
from src.telemetry.logger import logger

def parse_args(args_str: str) -> tuple[list[Any], dict[str, Any]]:
    """Parses tool call arguments safely from python-like function syntax or JSON.
    
    Examples:
        - "Đà Nẵng", "2025-06-20" -> (['Đà Nẵng', '2025-06-20'], {})
        - destination_city="Đà Nẵng", departure_date="2025-06-20" -> ([], {'destination_city': 'Đà Nẵng', 'departure_date': '2025-06-20'})
        - {"destination_city": "Đà Nẵng"} -> ([], {'destination_city': 'Đà Nẵng'})
    """
    args_str = args_str.strip()
    try:
        # Wrap in a dummy function call to parse with ast.parse
        tree = ast.parse(f"f({args_str})")
        call_node = tree.body[0].value
        
        args = []
        for arg in call_node.args:
            args.append(ast.literal_eval(arg))
            
        kwargs = {}
        for kw in call_node.keywords:
            kwargs[kw.arg] = ast.literal_eval(kw.value)
            
        return args, kwargs
    except Exception:
        # Fallback to JSON dictionary if possible
        try:
            import json
            data = json.loads(args_str)
            if isinstance(data, dict):
                return [], data
            return [data], {}
        except Exception:
            # Fallback to simple comma splitting
            parts = [p.strip().strip('"').strip("'") for p in args_str.split(',') if p.strip()]
            return parts, {}


class ReActAgent:
    """
    A ReAct-style Agent that follows the Thought-Action-Observation loop.
    Implements core reasoning loop logic and tool execution.
    """
    
    def __init__(self, llm: LLMProvider, tools: List[Dict[str, Any]], max_steps: int = 5):
        self.llm = llm
        self.tools = tools
        self.max_steps = max_steps
        self.history = []

    def get_system_prompt(self) -> str:
        """
        The system prompt that instructs the agent to follow ReAct and its travel rules.
        """
        tool_descriptions = "\n".join([f"- {t['name']}: {t['description']}" for t in self.tools])
        return f"""You are a Travel Planning Assistant helping users find suitable flights and hotels.

You have access to the following tools:
{tool_descriptions}

CRITICAL FORMAT RULES FOR ALL TURNS:
1. You must output ONLY ONE 'Thought' and ONE 'Action' at a time.
2. After writing the "Action: tool_name(arguments)", you MUST IMMEDIATELY STOP generating text. Do not continue typing anything else.
3. NEVER write the word "Observation:" or hallucinate the tool results yourself. The system will provide the Observation for you in the next turn.

STRICT AGENT LOGIC:
1. ALWAYS call get_weather FIRST. If weather is bad (rain_prob > 0.7), warn the user in your "Final Answer" but still proceed with the search.
2. Call search_flights and hotel in PARALLEL (within the same turn).
   - If the user DOES NOT specify a hotel tier (budget/mid/luxury), you MUST NOT call the hotel tool, and you MUST NOT guess. Stop immediately and ask the user to clarify the tier using "Final Answer".
3. NEVER call calculate_total_price unless you have both a valid 'flight_id' (from search_flights) and 'hotel_id' (from hotel).
4. EDGE CASE: If search_flights returns an empty list [], you MUST immediately stop, suggest ±1 day near the departure date, and output your "Final Answer". Do not call hotel or calculate_total_price in this case.

RESPONSE FORMATS:
If you need more information from the user (e.g., missing hotel tier):
Final Answer: [Đặt câu hỏi tự nhiên bằng Tiếng Việt để hỏi lại thông tin phân khúc khách sạn]

If you have completed the search:
Final Answer: [Phản hồi đầy đủ bằng Tiếng Việt: thông tin thời tiết điểm đến, top chuyến bay, top khách sạn, và tổng chi phí so sánh với budget của người dùng nếu có]
"""

    def run(self, user_input: str) -> str:
        """
        Executes the ReAct thought-action-observation loop.
        """
        logger.log_event("AGENT_START", {"input": user_input, "model": self.llm.model_name})
        
        prompt = f"User: {user_input}\n"
        steps = 0

        while steps < self.max_steps:
            # Generate response from model
            response = self.llm.generate(prompt, system_prompt=self.get_system_prompt(), stop=["Observation:", "Observation"])
            content = response["content"]
            
            # Log metrics using performance tracker
            if "usage" in response and "latency_ms" in response:
                from src.telemetry.metrics import tracker
                tracker.track_request(
                    provider=response.get("provider", "unknown"),
                    model=self.llm.model_name,
                    usage=response["usage"],
                    latency_ms=response["latency_ms"]
                )
            
            logger.log_event("AGENT_THOUGHT", {"step": steps, "content": content})
            
            # Append LLM's response to history
            prompt += f"{content}\n"
            
            # Parse actions (Action: tool_name(args))
            actions = re.findall(r"(?:Action|Action:)\s*(\w+)\((.*)\)", content)
            
            if not actions:
                break
            
            # Execute tool actions in parallel
            observations_str = ""
            for tool_name, tool_args in actions:
                observation = self._execute_tool(tool_name, tool_args)
                observations_str += f"Observation: {observation}\n"
                
            prompt += observations_str
            steps += 1
            
        logger.log_event("AGENT_END", {"steps": steps})
        
        # Parse Final Answer out of prompt or content
        final_answer_match = re.search(r"Final Answer:\s*(.*)", prompt, re.DOTALL)
        if final_answer_match:
            ans = final_answer_match.group(1).strip()
        else:
            ans = content.strip()
            
        # Clean any remaining thoughts/actions/observations from the final response
        cleaned_lines = []
        for line in ans.split("\n"):
            stripped = line.strip()
            if re.match(r"^(?:Thought|Action|Observation|Args|Lỗi khi thực thi|Tool)\s*:", stripped, re.IGNORECASE):
                continue
            cleaned_lines.append(line)
        return "\n".join(cleaned_lines).strip()

    def _execute_tool(self, tool_name: str, args: str) -> str:
        """
        Helper method to execute tools by name dynamically.
        """
        for tool in self.tools:
            if tool['name'] == tool_name:
                try:
                    args_parsed, kwargs_parsed = parse_args(args)
                    func = tool['func']
                    observation = func(*args_parsed, **kwargs_parsed)
                    return str(observation)
                except Exception as e:
                    return f"Lỗi khi thực thi '{tool_name}': {type(e).__name__}: {e}"
        return f"Tool '{tool_name}' không tồn tại."

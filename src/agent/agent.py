import os
import re
from typing import List, Dict, Any, Optional
from src.core.llm_provider import LLMProvider
from src.telemetry.logger import logger

class ReActAgent:
    """
    SKELETON: A ReAct-style Agent that follows the Thought-Action-Observation loop.
    Students should implement the core loop logic and tool execution.
    """
    
    def __init__(self, llm: LLMProvider, tools: List[Dict[str, Any]], max_steps: int = 5):
        self.llm = llm
        self.tools = tools
        self.max_steps = max_steps
        self.history = []

    def get_system_prompt(self) -> str:
        """
        Generates the system prompt instructing the agent to act as a Travel Assistant
        and follow the Thought-Action-Observation ReAct pattern.
        """
        tool_descriptions = "\n".join([f"- {t['name']}: {t['description']}" for t in self.tools])
        return f"""You are an expert AI Travel Assistant designed to help users plan trips efficiently. You have access to a set of specialized tools for flights, hotels, weather, currency, and visa rules.

Available tools:
{tool_descriptions}

### Core Rules & Tool Usage:
1. Grounding: Never make up, hallucinate, or assume travel data (prices, flights, weather, visa policies). If you need this data, you MUST call the appropriate tool. If a tool fails or returns no data, inform the user honestly.
2. Multi-Step Execution (Tool Chaining): You can call multiple tools in a single turn or sequentially to solve a complex request. 
   - If a user asks "Can I travel to Japan and how much will it cost?", you must check visa requirements first, then search flights and hotels, and finally calculate the total price.
3. Proactive Currency Matching: If you detect a user is from a specific country or asks about a specific destination, automatically use `convert_currency` to display prices in their native currency alongside the local price.

### Interaction Workflow:
- Step 1: Analyze the user's intent to identify required parameters (cities, dates, nationalities).
- Step 2: Call the necessary tools. Do not answer before receiving the tool output.
- Step 3: Synthesize the tool responses into a conversational, scannable, and helpful response. Use markdown tables or bullet points for listings.

### Tone & Style:
Be welcoming, concise, and professional. Avoid lengthy introductory fluff. Get straight to the data and options.

### Format Instructions:
You MUST follow the ReAct format strictly. Every turn must start with a 'Thought:' block followed by either an 'Action:' block or a 'Final Answer:' block.
You MUST write exactly one Thought and one Action (or Final Answer) per turn. Do NOT write the Observation block yourself.

Format:
Thought: your line of reasoning about what tool is needed next.
Action: tool_name(param1="value1", param2=value2)
Observation: [The system will run the tool and show the output here]

Example Trace:
User: I am a Vietnamese tourist wanting to visit Singapore. How is the weather there, and is a visa required?
Thought: The user is a Vietnamese national traveling to Singapore. I need to check visa requirements first using check_visa_requirements and check the weather using get_weather. Let's start with checking visa requirements.
Action: check_visa_requirements(passport_nationality="Vietnam", destination_country="Singapore")
Observation: {{"visa_required": false, "max_stay_days": 30, "notes": "Visa exemption under bilateral agreements for tourist visits up to 30 days."}}
Thought: Visa is not required for Vietnamese citizens up to 30 days. Now I should check the weather in Singapore.
Action: get_weather(destination_city="Saigon", departure_date="2026-06-01")
Observation: {{"temp": 31.0, "rain_prob": 0.6, "condition": "Tropical Rain", "destination_city": "Singapore", "date": "2026-06-01"}}
Thought: I have retrieved both visa requirements and weather details. I can now compile the final response.
Final Answer: As a Vietnamese citizen, you do not need a visa to enter Singapore for stays up to 30 days. The weather is currently around 31.0°C with tropical rain (60% probability of rain), so remember to bring an umbrella!
"""

    def run(self, user_input: str) -> str:
        """
        Runs the ReAct loop, iterating until a final answer is achieved or max_steps is reached.
        """
        logger.log_event("AGENT_START", {"input": user_input, "model": self.llm.model_name})
        
        current_prompt = f"User: {user_input}"
        steps = 0

        while steps < self.max_steps:
            # 1. Generate response from the LLM
            response_dict = self.llm.generate(current_prompt, system_prompt=self.get_system_prompt())
            content = response_dict.get("content", "")
            
            logger.log_event("AGENT_STEP", {
                "step": steps + 1,
                "model_response": content,
                "latency_ms": response_dict.get("latency_ms", 0),
                "usage": response_dict.get("usage", {})
            })
            
            # Append LLM output to prompt history
            current_prompt += f"\n{content}"
            
            # 2. Check for Final Answer
            final_match = re.search(r"Final\s*Answer:\s*(.*)", content, re.DOTALL | re.IGNORECASE)
            if final_match:
                final_answer = final_match.group(1).strip()
                logger.log_event("AGENT_END", {"steps": steps + 1, "status": "SUCCESS", "final_answer": final_answer})
                return final_answer
                
            # 3. Parse action and arguments
            action_match = re.search(r"Action:\s*(\w+)\((.*)\)", content, re.IGNORECASE)
            
            # Fallback if Action prefix was omitted but function call structure exists
            if not action_match:
                action_match = re.search(r"(\w+)\((.*)\)", content)
                
            if action_match:
                tool_name = action_match.group(1)
                tool_args_str = action_match.group(2)
                
                # Execute tool
                observation = self._execute_tool(tool_name, tool_args_str)
                
                # Append Observation block
                current_prompt += f"\nObservation: {observation}"
                
                logger.log_event("TOOL_EXECUTION", {
                    "tool": tool_name,
                    "args": tool_args_str,
                    "observation": observation
                })
            else:
                logger.log_event("PARSING_ERROR", {"response": content})
                current_prompt += "\nObservation: Format error. You must think and call a tool using 'Action: tool_name(param=value)' or give the 'Final Answer: ...'."
            
            steps += 1
            
        logger.log_event("AGENT_END", {"steps": steps, "status": "TIMEOUT"})
        return f"Agent exceeded maximum step limit ({self.max_steps}). Last output: {content}"

    def _execute_tool(self, tool_name: str, args_str: str) -> str:
        """
        Helper method to execute tools by name.
        """
        for tool in self.tools:
            if tool['name'] == tool_name:
                kwargs = self._parse_args(args_str)
                try:
                    result = tool['func'](**kwargs)
                    return str(result)
                except Exception as e:
                    return f"Error executing tool {tool_name} with arguments {kwargs}: {str(e)}"
        return f"Tool {tool_name} not found."

    def _parse_args(self, args_str: str) -> Dict[str, Any]:
        """
        Parses python style keyword arguments: param="value", param=value or JSON.
        """
        args_str = args_str.strip()
        if args_str.startswith("{") and args_str.endswith("}"):
            try:
                import json
                return json.loads(args_str)
            except Exception:
                pass
                
        kwargs = {}
        pairs = re.findall(r'(\w+)\s*=\s*(?:"([^"]*)"|\'([^\']*)\'|([^\s,]+))', args_str)
        for pair in pairs:
            key = pair[0]
            val = pair[1] or pair[2] or pair[3]
            try:
                if '.' in val:
                    val = float(val)
                else:
                    val = int(val)
            except ValueError:
                pass
            kwargs[key] = val
        return kwargs

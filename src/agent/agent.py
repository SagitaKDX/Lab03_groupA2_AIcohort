import os
import re
from typing import List, Dict, Any, Optional
from src.core.llm_provider import LLMProvider
from src.telemetry.logger import logger
from src.tools.prompt import SYSTEM_PROMPT_TEMPLATE

class ReActAgent:
    """
    SKELETON: A ReAct-style Agent that follows the Thought-Action-Observation loop.
    Students should implement the core loop logic and tool execution.
    """
    
    def __init__(
        self,
        llm: LLMProvider,
        tools: List[Dict[str, Any]],
        max_steps: int = 5,
        prompt_template: str = "prompt_with_fewshot",
    ):
        self.llm = llm
        self.tools = tools
        self.max_steps = max_steps
        self.prompt_template = prompt_template
        self.history = []
        self.custom_system_prompt = None

    def get_system_prompt(self) -> str:
        """
        Generates the system prompt instructing the agent to act as a Travel Assistant
        and follow the Thought-Action-Observation ReAct pattern.
        """
        if self.custom_system_prompt is not None:
            return self.custom_system_prompt
            
        tool_descriptions = "\n".join([f"- {t['name']}: {t['description']}" for t in self.tools])
        template = SYSTEM_PROMPT_TEMPLATE.get(
            self.prompt_template,
            SYSTEM_PROMPT_TEMPLATE["prompt_with_fewshot"],
        )
        return template.format(tool_descriptions=tool_descriptions)

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

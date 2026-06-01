import os
import re
import json
import sys
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv
from src.core.llm_provider import LLMProvider
from src.core.openai_provider import OpenAIProvider
from src.core.gemini_provider import GeminiProvider
from src.core.local_provider import LocalProvider
from src.telemetry.logger import logger
from src.tools import search_flights, hotel, get_weather_tool, calculate_total_price
import src.tools as tools

class ReActAgent:
    """
    A robust ReAct-style Agent that follows the Thought-Action-Observation loop.
    Supports switching LLM providers (OpenAI, Gemini, Local GGUF) and parses
    text-based reasoning traces with resilient fallback handling.
    """
    
    def __init__(self, llm: LLMProvider, tools: List[Dict[str, Any]], max_steps: int = 6):
        self.llm = llm
        self.tools = tools
        self.max_steps = max_steps
        self.history = []

    def get_system_prompt(self) -> str:
        """
        Build a high-quality system prompt directing the agent to strictly
        reason via the ReAct framework and listing tool specifications.
        """
        tool_descriptions = []
        for t in self.tools:
            name = t.get('name') or t.get('function', {}).get('name')
            desc = t.get('description') or t.get('function', {}).get('description')
            tool_descriptions.append(f"- {name}: {desc}")
        tool_descriptions_str = "\n".join(tool_descriptions)
        
        return f"""Bạn là một AI Agent thông minh lập kế hoạch du lịch hoạt động theo mô hình ReAct (Reasoning and Acting).
Mục tiêu của bạn là giúp người dùng lên kế hoạch chuyến đi trọn vẹn thông qua việc kết hợp giữa suy luận (Thought) và hành động (Action - gọi tool).

Bạn có quyền truy cập vào các công cụ sau:
{tool_descriptions_str}

QUY TRÌNH HÀNH ĐỘNG NGHIÊM NGẶT:
Bạn phải sử dụng định dạng sau để suy nghĩ và hành động, KHÔNG ĐƯỢC THAY ĐỔI ĐỊNH DẠNG NÀY:
Thought: Suy nghĩ xem bạn đang ở bước nào, cần thêm thông tin gì để lên kế hoạch và gọi tool nào tiếp theo.
Action: tool_name(arguments)
Observation: Kết quả thực tế từ tool (Bạn KHÔNG tự viết dòng Observation này. Hệ thống sẽ tự động chạy tool và trả về kết quả cho bạn).

... (Lặp lại cặp Thought / Action / Observation nếu cần thiết)

Final Answer: Câu trả lời cuối cùng, chi tiết, mạch lạc và thân thiện cho người dùng sau khi đã có đầy đủ thông tin từ tất cả các công cụ.

⚠️ YÊU CẦU CỰC KỲ QUAN TRỌNG:
1. Bạn phải hoàn thành tất cả các bước tra cứu: Tìm chuyến bay -> Tìm khách sạn -> Kiểm tra thời tiết -> Tính tổng chi phí trước khi đưa ra câu trả lời cuối cùng.
2. KHÔNG ĐƯỢC tự bịa ra thông tin mã chuyến bay (flight_id), mã khách sạn (hotel_id), thời tiết hoặc giá tiền. Mọi thông tin phải đến từ kết quả Observation của các công cụ.
3. BẮT BUỘC sử dụng chính xác mã `hotel_id` và `flight_id` được liệt kê rõ ràng trong kết quả Observation của các công cụ trước đó. Ví dụ, nếu công cụ `hotel` trả về `[{{"hotel_id": "IBIS_PARIS", ...}}]`, bạn PHẢI truyền `hotel_id="IBIS_PARIS"` cho công cụ `calculate_total_price`. TUYỆT ĐỐI KHÔNG tự chế mã khác như `HILTON4`, `HILTON_PARIS`, v.v. nếu nó không xuất hiện trong Observation.
4. Khi gọi Action, hãy viết đúng cú pháp Python như: `search_flights(departure_city="Hà Nội", destination_city="Paris", departure_date="ngày mai")` hoặc JSON `search_flights({{"departure_city": "Hà Nội", ...}})` hoặc dạng đơn giản `search_flights(departure_city="Hà Nội", destination_city="Paris", departure_date="ngày mai")`.
5. Chỉ thực hiện MỘT Action tại mỗi bước. Đợi Observation trước khi tiếp tục Thought tiếp theo.
6. Khi tính tổng chi phí, bắt buộc phải sử dụng công cụ `calculate_total_price` với mã flight_id và hotel_id thực tế đã tìm thấy được qua tool.
"""

    def run(self, user_input: str) -> str:
        """
        Executes the ReAct reasoning loop.
        """
        logger.log_event("AGENT_START", {"input": user_input, "model": self.llm.model_name})
        
        # We start with the user input and build our reasoning chain
        history_text = f"User query: {user_input}\n"
        
        print("\n" + "="*80)
        print(f"🎬 BẮT ĐẦU CHẠY AGENT - CÂU HỎI: \"{user_input}\"")
        print(f"⚙️  MÔ HÌNH: {self.llm.model_name}")
        print("="*80)
        
        steps = 0
        final_answer = None

        while steps < self.max_steps:
            print(f"\n--- [VÒNG LẶP REACT BƯỚC {steps + 1}/{self.max_steps}] ---")
            
            # Generate next step from LLM
            response_dict = self.llm.generate(prompt=history_text, system_prompt=self.get_system_prompt())
            
            # Log metrics
            logger.log_event("LLM_METRIC", {
                "provider": response_dict.get("provider"),
                "model": self.llm.model_name,
                "latency_ms": response_dict.get("latency_ms"),
                "usage": response_dict.get("usage")
            })
            
            content = response_dict["content"].strip()
            
            # Append LLM's response to history
            history_text += f"{content}\n"
            
            # Parse thought, action and final answer
            thought_match = re.search(r'Thought:\s*(.*?)(?:Action:|Final Answer:|$)', content, re.DOTALL)
            action_match = re.search(r'Action:\s*(\w+)\s*\((.*)\)', content)
            if not action_match:
                action_match = re.search(r'Action:\s*(\w+)\s*(\{.*\})', content, re.DOTALL)
                
            final_answer_match = re.search(r'Final Answer:\s*(.*)', content, re.DOTALL)
            
            # Print thought
            if thought_match:
                thought_str = thought_match.group(1).strip()
                if thought_str:
                    print(f"🧠 [Thought]:\n{thought_str}")
            else:
                # Fallback if model skips Thought prefix
                if not action_match and not final_answer_match:
                    print(f"🧠 [Thought]:\n{content}")
                    
            # Check Action
            if action_match:
                tool_name = action_match.group(1).strip()
                args_str = action_match.group(2).strip()
                
                print(f"🎬 [Action] -> Gọi Tool: '{tool_name}'")
                print(f"   └─ Tham số đầu vào: {args_str}")
                
                # Execute tool
                observation = self._execute_tool(tool_name, args_str)
                print(f"👁️‍🗨️ [Observation] -> Kết quả thực tế thu được:")
                print(f"   └─ {observation}")
                
                # Append Observation back to history so LLM can read it in the next turn
                history_text += f"Observation: {observation}\n"
                
            # Check Final Answer
            elif final_answer_match:
                final_answer = final_answer_match.group(1).strip()
                print("\n✨ [Final Answer]:")
                print(final_answer)
                print("="*80)
                break
            else:
                # Fallback if no explicit marker matches but text contains it
                if "Final Answer:" in content:
                    parts = content.split("Final Answer:")
                    final_answer = parts[-1].strip()
                    print("\n✨ [Final Answer]:")
                    print(final_answer)
                    print("="*80)
                    break
                elif not action_match:
                    # Treat the LLM's response as the final answer if it's the last step or no tool was called
                    final_answer = content
                    print("\n✨ [Final Answer]:")
                    print(final_answer)
                    print("="*80)
                    break

            steps += 1
            
        if steps >= self.max_steps and not final_answer:
            print("\n🛑 Stopped: max iterations reached! Vòng lặp bị ngắt để tránh lặp vô hạn.")
            print("="*80)
            final_answer = "Stopped: max iterations reached"

        logger.log_event("AGENT_END", {"steps": steps})
        return final_answer

    def _execute_tool(self, tool_name: str, args_str: str) -> str:
        """
        Helper method to execute tools by name with robust JSON and kwargs parsing.
        """
        try:
            parsed_args = self._parse_args(args_str)
            
            if tool_name == "search_flights":
                result = search_flights(**parsed_args)
            elif tool_name == "hotel":
                if "rate" in parsed_args:
                    parsed_args["rate"] = int(parsed_args["rate"])
                result = hotel(**parsed_args)
            elif tool_name == "get_weather":
                result = get_weather_tool(**parsed_args)
            elif tool_name == "calculate_total_price":
                result = calculate_total_price(**parsed_args)
            else:
                return f"Lỗi: Không tìm thấy công cụ nào có tên là '{tool_name}'."
                
            return json.dumps(result, ensure_ascii=False)
        except Exception as tool_error:
            return f"Lỗi phát sinh từ công cụ: {str(tool_error)}"

    def _parse_args(self, args_str: str) -> dict:
        """
        Parses python arguments (e.g. k1="v1", k2=v2) or JSON-style objects into a dict.
        """
        args_str = args_str.strip()
        if not args_str:
            return {}
            
        # Try JSON parsing
        try:
            # Clean up potential markdown code block wraps like ```json ... ```
            clean_str = args_str
            if clean_str.startswith("```"):
                clean_str = re.sub(r'^```(?:json)?\n|```$', '', clean_str, flags=re.MULTILINE).strip()
            return json.loads(clean_str)
        except Exception:
            pass
            
        # Try parsing python-style keyword arguments
        parsed = {}
        
        # 1. Match key = "value" or key = 'value'
        quoted_pattern = r'(\w+)\s*=\s*([\'"])(.*?)\2'
        for key, _, val in re.findall(quoted_pattern, args_str):
            parsed[key] = val
            
        # 2. Match key = 123
        num_pattern = r'(\w+)\s*=\s*(\d+)'
        for key, val in re.findall(num_pattern, args_str):
            parsed[key] = int(val)
            
        # 3. Match unquoted words (excluding matched keys, handles booleans etc.)
        word_pattern = r'(\w+)\s*=\s*([a-zA-Z0-9_\u00C0-\u1EF9]+)'
        for key, val in re.findall(word_pattern, args_str):
            if key not in parsed:
                if val.lower() == 'true':
                    parsed[key] = True
                elif val.lower() == 'false':
                    parsed[key] = False
                else:
                    parsed[key] = val
                    
        return parsed

if __name__ == "__main__":
    # Ensure Windows console can display UTF-8 (Emoji) without encoding errors
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

    # Ensure the root directory is in python path so it runs from anywhere
    sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

    # Load environment variables from .env
    load_dotenv()

    # Create optional CLI arguments
    import argparse
    parser = argparse.ArgumentParser(description="ReAct Agent Travel Planner")
    parser.add_argument(
        "--provider", 
        type=str, 
        choices=["openai", "google", "local"], 
        default=os.getenv("DEFAULT_PROVIDER", "openai"),
        help="LLM provider (defaults to DEFAULT_PROVIDER in .env)"
    )
    parser.add_argument(
        "--model", 
        type=str, 
        default=os.getenv("DEFAULT_MODEL", "gpt-4o"),
        help="Model name (defaults to DEFAULT_MODEL in .env)"
    )
    parser.add_argument(
        "--query", 
        type=str, 
        default="Tôi muốn bay từ Hà Nội đến Paris vào ngày mai. Hãy giúp tôi tìm chuyến bay phù hợp, tìm khách sạn 4 sao tại điểm đến, kiểm tra thời tiết ở điểm đến và tính tổng chi phí chuyến đi giúp tôi nhé!",
        help="User query for the ReAct Agent"
    )
    parser.add_argument(
        "--simulate-error", 
        action="store_true",
        help="Simulate a weather station connection timeout error"
    )
    
    args = parser.parse_args()
    
    provider_name = args.provider.lower()
    model_name = args.model
    
    # Configure simulated error
    if args.simulate_error:
        tools.SIMULATE_ERROR = True
        print("⚠️ HỆ THỐNG: Kích hoạt kịch bản giả lập lỗi khí tượng (SIMULATE_ERROR = True)")
    else:
        tools.SIMULATE_ERROR = False

    print("\n" + "="*80)
    print(f"⚙️  HỆ THỐNG: Khởi tạo hoàn tất từ tệp cấu hình .env")
    print(f"   ├─ Nhà cung cấp (PROVIDER): {provider_name}")
    print(f"   ├─ Mô hình (MODEL): {model_name}")
    print(f"   └─ Giả lập lỗi (SIMULATE_ERROR): {tools.SIMULATE_ERROR}")
    print("="*80)

    # Initialize the corresponding LLM Provider
    if provider_name == "openai":
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key or api_key.startswith("your_"):
            print("❌ LỖI: Chưa cấu hình OPENAI_API_KEY trong file .env hoặc đang dùng key mặc định.")
            sys.exit(1)
        provider = OpenAIProvider(model_name=model_name, api_key=api_key)
        
    elif provider_name == "google":
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key or api_key.startswith("your_"):
            print("❌ LỖI: Chưa cấu hình GEMINI_API_KEY trong file .env hoặc đang dùng key mặc định.")
            sys.exit(1)
        provider = GeminiProvider(model_name=model_name, api_key=api_key)
        
    elif provider_name == "local":
        model_path = os.getenv("LOCAL_MODEL_PATH", "./models/Phi-3-mini-4k-instruct-q4.gguf")
        if not os.path.exists(model_path):
            print(f"❌ LỖI: Không tìm thấy tệp mô hình GGUF tại {model_path}.")
            print("Vui lòng tải mô hình Phi-3 từ Hugging Face và lưu vào thư mục models/.")
            sys.exit(1)
        print(f"🔌 Khởi tạo mô hình cục bộ từ: {model_path} (Có thể mất vài giây...)")
        provider = LocalProvider(model_path=model_path)
        
    else:
        print(f"❌ LỖI: Nhà cung cấp '{provider_name}' không được hỗ trợ.")
        sys.exit(1)

    # Initialize ReAct Agent
    agent = ReActAgent(
        llm=provider,
        tools=tools.TOOLS,
        max_steps=6
    )

    try:
        agent.run(args.query)
    except Exception as e:
        print(f"\n❌ LỖI trong quá trình chạy Agent: {e}")

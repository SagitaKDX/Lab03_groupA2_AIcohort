"""Test script to run the Travel Finder ReAct Agent using OpenAI Provider.
"""

import os
import sys
from dotenv import load_dotenv

# Ensure the root of the lab folder is in sys.path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.core.openai_provider import OpenAIProvider
from src.agent.agent import ReActAgent
from src.tools.travel_tools import ALL_TOOLS

def main():
    load_dotenv()
    
    # Configure provider with local proxy model
    model_name = "groq/llama-3.1-8b-instant"
    print(f"Initializing OpenAI Provider with model: {model_name}...")
    llm = OpenAIProvider(model_name=model_name)
    
    # Instantiate ReAct agent
    print("Instantiating ReActAgent with mock travel tools...")
    agent = ReActAgent(llm=llm, tools=ALL_TOOLS, max_steps=5)
    
    test_cases = [
        (
            "Test 1 - Đầy đủ luồng (Thời tiết xấu, mid hotel, trong budget)",
            "Tìm chuyến đi Đà Nẵng từ Hà Nội ngày 2025-06-20, khách sạn tầm trung, budget khoảng 2 triệu"
        ),
        (
            "Test 2 - Edge case: Không có chuyến bay (Suggest ngày lân cận)",
            "Tìm chuyến đi Sài Gòn từ Hà Nội ngày 2025-06-20, khách sạn tầm trung"
        ),
        (
            "Test 3 - Điểm đến không nhận diện / Hỏi lại phân khúc",
            "Tìm chuyến đi Đà Nẵng từ Hà Nội ngày 2025-06-20, budget khoảng 2 triệu"
        )
    ]

    for label, query in test_cases:
        print("\n" + "=" * 60)
        print(f"Test: {label}")
        print(f"Input: {query}")
        print("=" * 60)
        
        try:
            # ReActAgent.run outputs step logs to console/file through logger.log_event
            final_answer = agent.run(query)
            print(f"\nFinal Answer:\n{final_answer}")
        except Exception as e:
            print(f"Execution failed: {e}")

if __name__ == "__main__":
    main()

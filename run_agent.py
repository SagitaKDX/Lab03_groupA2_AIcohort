import os
import sys
from dotenv import load_dotenv

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

def get_provider():
    provider_name = os.getenv("DEFAULT_PROVIDER", "openai").lower()
    
    if provider_name == "openai" or provider_name == "openai":
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key or api_key == "your_openai_api_key_here":
            print("⚠️  Warning: OPENAI_API_KEY is not set or has placeholder value in .env.")
        model_name = os.getenv("DEFAULT_MODEL", "gpt-4o")
        print(f"Using OpenAI Provider with model: {model_name}")
        return OpenAIProvider(model_name=model_name, api_key=api_key)
        
    elif provider_name == "google" or provider_name == "gemini":
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key or api_key == "your_gemini_api_key_here":
            print("⚠️  Warning: GEMINI_API_KEY is not set or has placeholder value in .env.")
        # Default Gemini model
        model_name = "gemini-2.5-flash"
        print(f"Using Gemini Provider with model: {model_name}")
        return GeminiProvider(model_name=model_name, api_key=api_key)
        
    else:
        raise ValueError(f"Unknown or unsupported provider: {provider_name}")

def main():
    load_dotenv()
    
    # 1. Initialize tools list
    tools_list = [
        {
            "name": "search_flights",
            "description": 'search_flights(departure_city: str, destination_city: str, departure_date: str) -> Searches flight options and prices (in USD). Example: search_flights(departure_city="Hanoi", destination_city="Tokyo", departure_date="2026-07-01")',
            "func": travel_tools.search_flights
        },
        {
            "name": "search_hotels",
            "description": 'search_hotels(destination_city: str, rate: int) -> Searches hotel prices per night (in USD) based on star rating/class (1 to 5). Example: search_hotels(destination_city="Tokyo", rate=4)',
            "func": travel_tools.search_hotels
        },
        {
            "name": "get_weather",
            "description": 'get_weather(destination_city: str, departure_date: str) -> Checks weather temperature (C) and rain probability. Example: get_weather(destination_city="Tokyo", departure_date="2026-07-01")',
            "func": travel_tools.get_weather
        },
        {
            "name": "calculate_total_price",
            "description": 'calculate_total_price(flight_id: str, hotel_id: str) -> Calculates total trip cost (flight + 3 nights hotel). Example: calculate_total_price(flight_id="VN-310", hotel_id="HT-TOKYO-Comfort")',
            "func": travel_tools.calculate_total_price
        },
        {
            "name": "convert_currency",
            "description": 'convert_currency(base_currency: str, target_currency: str, amount: float) -> Converts price from base to target currency. Example: convert_currency(base_currency="USD", target_currency="VND", amount=570.0)',
            "func": travel_tools.convert_currency
        },
        {
            "name": "check_visa_requirements",
            "description": 'check_visa_requirements(passport_nationality: str, destination_country: str) -> Checks visa requirement status and notes. Example: check_visa_requirements(passport_nationality="Vietnam", destination_country="Japan")',
            "func": travel_tools.check_visa_requirements
        },
        {
            "name": "get_current_time",
            "description": 'get_current_time(timezone: str) -> Returns current date/time in specified IANA timezone. Example: get_current_time(timezone="Asia/Ho_Chi_Minh")',
            "func": travel_tools.get_current_time
        },
        {
            "name": "get_airport_transfer",
            "description": 'get_airport_transfer(city: str, transfer_type: str = "all") -> Provides information about airport transfers in a given city. Example: get_airport_transfer(city="Tokyo", transfer_type="taxi")',
            "func": travel_tools.get_airport_transfer
        }
    ]
    
    # 2. Get the LLM Provider
    try:
        llm = get_provider()
    except Exception as e:
        print(f"❌ Error initializing LLM provider: {e}")
        return

    # 3. Instantiate ReActAgent
    # Increase max_steps to 7 since checking visa, flights, hotels, calculations, and conversions takes multiple steps
    agent = ReActAgent(llm=llm, tools=tools_list, max_steps=10)
    
    # 4. Define test query
    query = (
        "I am a Vietnamese tourist wanting to travel from Hanoi to Tokyo on 2026-07-01. "
        "Can I travel there, how will the weather be, and what is the total price for a flight and a 4-star hotel stay (USD and VND)?"
    )
    
    print("\n--- Starting Travel Assistant Agent Session ---")
    print(f"Query: {query}\n")
    
    try:
        final_answer = agent.run(query)
        print("\n--- Final Output ---")
        print(final_answer)
    except Exception as e:
        print(f"\n❌ Error running agent: {e}")

if __name__ == "__main__":
    main()

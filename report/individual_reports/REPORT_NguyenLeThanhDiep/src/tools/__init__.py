# Tools Facade to bundle and export all custom tools and schemas

from .search_flights import search_flights, SCHEMA as flights_schema
from .hotel import hotel, SCHEMA as hotel_schema
from .get_weather import get_weather, SCHEMA as weather_schema
from .calculate_total_price import calculate_total_price, SCHEMA as price_schema
from . import get_weather as gw

SIMULATE_ERROR = False

def get_weather_tool(destination_city: str, departure_date: str) -> dict:
    # Synchronize the SIMULATE_ERROR flag to get_weather module
    gw.SIMULATE_ERROR = SIMULATE_ERROR
    return get_weather(destination_city, departure_date)

TOOLS = [
    flights_schema,
    hotel_schema,
    weather_schema,
    price_schema
]

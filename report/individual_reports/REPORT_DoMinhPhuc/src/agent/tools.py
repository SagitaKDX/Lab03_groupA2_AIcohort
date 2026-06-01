def search_flights(source: str, destination: str, date: str) -> str:
    """Returns available flights and prices. date format: YYYY-MM-DD."""
    db = {
        ("hanoi", "tokyo"):     [("VN307", "Vietnam Airlines", 420.0), ("JL751", "Japan Airlines", 510.0)],
        ("hanoi", "singapore"): [("SQ185", "Singapore Airlines", 210.0), ("VN641", "Vietnam Airlines", 180.0)],
        ("ho chi minh", "tokyo"): [("VN300", "Vietnam Airlines", 390.0)],
    }
    rows = db.get((source.strip().lower(), destination.strip().lower()))
    if not rows:
        return f"No flights found from {source} to {destination} on {date}."
    return "\n".join(f"{flt} ({airline}) ${price:.2f}" for flt, airline, price in rows)

def search_hotel(location: str, checkin_date: str, checkout_date: str) -> str:
    """Returns hotels and nightly rates. Multiply price × nights before passing to calculate_total_price."""
    db = {
        "tokyo":     [("Shinjuku Grand Hotel", 4, 95.0), ("Tokyo Bay Marriott", 5, 210.0)],
        "singapore": [("Marina Bay Sands", 5, 380.0), ("Ibis Budget Novena", 2, 60.0)],
        "hanoi":     [("Sofitel Metropole", 5, 250.0), ("La Siesta Hotel", 4, 75.0)],
    }
    rows = db.get(location.strip().lower())
    if not rows:
        return f"No hotels found in {location}."
    return "\n".join(f"{'⭐'*s} {name} ${price:.2f}/night" for name, s, price in rows)

def get_weather(location: str, date: str) -> str:
    """Returns weather forecast for a city on a given date (YYYY-MM-DD)."""
    db = {
        "tokyo":     "Partly Cloudy, 26°C, humidity 70% — carry an umbrella.",
        "singapore": "Thunderstorms, 31°C, humidity 88% — expect afternoon showers.",
        "hanoi":     "Sunny, 34°C, humidity 65% — stay hydrated.",
    }
    return db.get(location.strip().lower(), f"No weather data for {location}.")

def calculate_total_price(flight_price: float, hotel_price: float, tax_rate: float) -> str:
    """Returns grand total with tax. tax_rate is a decimal: 0.10 = 10% — never pass 10."""
    if not (0.0 <= tax_rate <= 1.0):
        return f"Error: tax_rate must be 0.0–1.0 (e.g. 0.10 for 10%), got {tax_rate}"
    total = round((flight_price + hotel_price) * (1 + tax_rate), 2)
    return f"Total: ${total:.2f} (subtotal ${flight_price + hotel_price:.2f} + {tax_rate*100:.0f}% tax)"

TOOLS = {
    "search_flights":        search_flights,
    "search_hotel":          search_hotel,
    "get_weather":           get_weather,
    "calculate_total_price": calculate_total_price,
}
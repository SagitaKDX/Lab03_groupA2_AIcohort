from typing import Dict, Any

def search_flights(departure_city: str, destination_city: str, departure_date: str) -> Dict[str, Any]:
    """
    Search for flights matching the departure, destination, and date.
    Returns a dictionary containing 'flight_id' and 'price' (in USD).
    """
    # Simple deterministic mock data
    key = f"{departure_city.lower()}_{destination_city.lower()}"
    flights = {
        "hanoi_tokyo": {"flight_id": "VN-310", "price": 450.0},
        "hanoi_singapore": {"flight_id": "SQ-175", "price": 250.0},
        "saigon_tokyo": {"flight_id": "JL-752", "price": 500.0},
        "newyork_tokyo": {"flight_id": "AA-167", "price": 950.0},
    }
    
    result = flights.get(key, {"flight_id": "FL-GENERIC", "price": 350.0})
    return {
        "flight_id": result["flight_id"],
        "price": result["price"],
        "departure_city": departure_city,
        "destination_city": destination_city,
        "departure_date": departure_date
    }

def search_hotels(destination_city: str, rate: int) -> Dict[str, Any]:
    """
    Search for hotels in the destination city by star rating/class (1 to 5).
    Returns a dictionary containing 'hotel_id' and 'price' per night (in USD).
    """
    dest = destination_city.lower()
    # Simple mock rate multipliers
    base_price = 50.0 * max(1, min(5, rate))
    
    hotels = {
        "tokyo": {"hotel_id": "HT-TOKYO-Luxe" if rate >= 4 else "HT-TOKYO-Comfort", "price": base_price + 30.0},
        "singapore": {"hotel_id": "HT-SG-Marina" if rate >= 4 else "HT-SG-Budget", "price": base_price + 40.0},
    }
    
    result = hotels.get(dest, {"hotel_id": f"HT-{destination_city.upper()}-GEN", "price": base_price})
    return {
        "hotel_id": result["hotel_id"],
        "price": result["price"],
        "destination_city": destination_city,
        "star_rating": rate
    }

def get_weather(destination_city: str, departure_date: str) -> Dict[str, Any]:
    """
    Get weather forecast details for the destination city on the departure date.
    Returns temp (in Celsius) and rain probability.
    """
    dest = destination_city.lower()
    weather_data = {
        "tokyo": {"temp": 22.0, "rain_prob": 0.15, "condition": "Partly Cloudy"},
        "singapore": {"temp": 31.0, "rain_prob": 0.60, "condition": "Tropical Rain"},
    }
    result = weather_data.get(dest, {"temp": 25.0, "rain_prob": 0.30, "condition": "Sunny"})
    return {
        "temp": result["temp"],
        "rain_prob": result["rain_prob"],
        "condition": result["condition"],
        "destination_city": destination_city,
        "date": departure_date
    }

def calculate_total_price(flight_id: str, hotel_id: str) -> Dict[str, Any]:
    """
    Calculate the total price based on the selected flight ID and hotel ID.
    Assumes a fixed stay duration of 3 nights for hotel calculation.
    """
    # Look up prices based on IDs
    flight_prices = {
        "VN-310": 450.0,
        "SQ-175": 250.0,
        "JL-752": 500.0,
        "AA-167": 950.0,
        "FL-GENERIC": 350.0
    }
    hotel_prices = {
        "HT-TOKYO-Luxe": 230.0,
        "HT-TOKYO-Comfort": 130.0,
        "HT-SG-Marina": 240.0,
        "HT-SG-Budget": 140.0
    }
    
    f_price = flight_prices.get(flight_id, 300.0)
    # Extract city prefix from hotel ID if not explicitly found in rates
    h_price = hotel_prices.get(hotel_id, 100.0)
    
    # Calculate for flight + 3 nights hotel
    total = f_price + (h_price * 3)
    return {
        "flight_price": f_price,
        "hotel_price_per_night": h_price,
        "nights": 3,
        "total_price": total
    }

def convert_currency(base_currency: str, target_currency: str, amount: float) -> Dict[str, Any]:
    """
    Convert currency from base currency (e.g. USD) to target currency (e.g. VND, JPY, EUR).
    """
    base = base_currency.upper()
    target = target_currency.upper()
    
    rates = {
        ("USD", "VND"): 25400.0,
        ("VND", "USD"): 1.0 / 25400.0,
        ("USD", "JPY"): 156.5,
        ("JPY", "USD"): 1.0 / 156.5,
        ("USD", "EUR"): 0.92,
        ("EUR", "USD"): 1.0 / 0.92,
        ("USD", "SGD"): 1.35,
        ("SGD", "USD"): 1.0 / 1.35,
    }
    
    if base == target:
        rate = 1.0
    else:
        rate = rates.get((base, target), 1.0)
        
    converted = amount * rate
    return {
        "base_currency": base,
        "target_currency": target,
        "original_amount": amount,
        "converted_amount": round(converted, 2),
        "exchange_rate": rate
    }

def check_visa_requirements(passport_nationality: str, destination_country: str) -> Dict[str, Any]:
    """
    Verify visa requirements for passport holder of a given nationality to destination country.
    """
    nat = passport_nationality.strip().lower()
    dest = destination_country.strip().lower()
    
    # Simple routing rules
    if nat == "vietnam" or nat == "vietnamese":
        if dest == "japan":
            return {
                "visa_required": True,
                "max_stay_days": 15,
                "notes": "Short-term tourist visa is required. Vietnam passport holders can apply for an e-visa via authorized agencies."
            }
        elif dest == "singapore":
            return {
                "visa_required": False,
                "max_stay_days": 30,
                "notes": "Visa exemption under bilateral agreements for tourist visits up to 30 days."
            }
    elif nat == "us" or nat == "usa" or nat == "american":
        if dest == "japan":
            return {
                "visa_required": False,
                "max_stay_days": 90,
                "notes": "Visa exemption for tourism, business, and visiting relatives up to 90 days."
            }
            
    # Default fallback
    return {
        "visa_required": True,
        "max_stay_days": 30,
        "notes": f"Standard tourist visa is generally required for {passport_nationality} citizens traveling to {destination_country}."
    }

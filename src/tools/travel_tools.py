import os
import csv
from datetime import datetime
from typing import Dict, Any

# Resolve CSV file paths relative to project root
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
FLIGHTS_CSV = os.path.join(BASE_DIR, "data", "flights.csv")
HOTELS_CSV = os.path.join(BASE_DIR, "data", "hotels.csv")
WEATHER_CSV = os.path.join(BASE_DIR, "data", "weather.csv")
CURRENCIES_CSV = os.path.join(BASE_DIR, "data", "currencies.csv")
VISA_CSV = os.path.join(BASE_DIR, "data", "visa_rules.csv")

def search_flights(departure_city: str, destination_city: str, departure_date: str) -> Dict[str, Any]:
    """
    Search for flights matching the departure, destination, and date.
    Returns a dictionary containing 'flight_id' and 'price' (in USD).
    """
    dep_city = departure_city.strip().lower()
    dest_city = destination_city.strip().lower()
    dep_date = departure_date.strip()
    
    if os.path.exists(FLIGHTS_CSV):
        with open(FLIGHTS_CSV, mode="r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if (row["departure_city"].strip().lower() == dep_city and 
                    row["destination_city"].strip().lower() == dest_city and 
                    row["departure_date"].strip() == dep_date):
                    return {
                        "flight_id": row["flight_id"],
                        "price": float(row["price"]),
                        "departure_city": row["departure_city"],
                        "destination_city": row["destination_city"],
                        "departure_date": row["departure_date"]
                    }
    
    # Fallback default
    return {
        "flight_id": "FL-GENERIC",
        "price": 350.0,
        "departure_city": departure_city,
        "destination_city": destination_city,
        "departure_date": departure_date
    }

def search_hotels(destination_city: str, rate: int) -> Dict[str, Any]:
    """
    Search for hotels in the destination city by star rating/class (1 to 5).
    Returns a dictionary containing 'hotel_id' and 'price' per night (in USD).
    """
    dest_city = destination_city.strip().lower()
    
    if os.path.exists(HOTELS_CSV):
        with open(HOTELS_CSV, mode="r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if (row["destination_city"].strip().lower() == dest_city and 
                    int(row["star_rating"]) == int(rate)):
                    return {
                        "hotel_id": row["hotel_id"],
                        "price": float(row["price"]),
                        "destination_city": row["destination_city"],
                        "star_rating": int(rate)
                    }
                    
    # Fallback default
    return {
        "hotel_id": f"HT-{destination_city.upper()}-GEN",
        "price": 50.0 * max(1, min(5, int(rate))),
        "destination_city": destination_city,
        "star_rating": int(rate)
    }

def get_weather(destination_city: str, departure_date: str) -> Dict[str, Any]:
    """
    Get weather forecast details for the destination city on the departure date.
    Returns temp (in Celsius) and rain probability.
    """
    dest_city = destination_city.strip().lower()
    dep_date = departure_date.strip()
    
    if os.path.exists(WEATHER_CSV):
        with open(WEATHER_CSV, mode="r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if (row["destination_city"].strip().lower() == dest_city and 
                    row["date"].strip() == dep_date):
                    return {
                        "temp": float(row["temp"]),
                        "rain_prob": float(row["rain_prob"]),
                        "condition": row["condition"],
                        "destination_city": row["destination_city"],
                        "date": row["date"]
                    }
                    
    # Fallback default
    return {
        "temp": 25.0,
        "rain_prob": 0.30,
        "condition": "Sunny",
        "destination_city": destination_city,
        "date": departure_date
    }

def calculate_total_price(flight_id: str, hotel_id: str) -> Dict[str, Any]:
    """
    Calculate the total price based on the selected flight ID and hotel ID.
    Assumes a fixed stay duration of 3 nights for hotel calculation.
    """
    f_price = None
    h_price = None
    
    if os.path.exists(FLIGHTS_CSV):
        with open(FLIGHTS_CSV, mode="r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row["flight_id"].strip().lower() == flight_id.strip().lower():
                    f_price = float(row["price"])
                    break
                    
    if os.path.exists(HOTELS_CSV):
        with open(HOTELS_CSV, mode="r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row["hotel_id"].strip().lower() == hotel_id.strip().lower():
                    h_price = float(row["price"])
                    break
                    
    if f_price is None:
        f_price = 350.0
    if h_price is None:
        h_price = 100.0
        
    total = f_price + (h_price * 3)
    return {
        "flight_price": f_price,
        "hotel_price_per_night": h_price,
        "nights": 3,
        "total_price": total
    }

def convert_currency(base_currency: str, target_currency: str, amount: float) -> Dict[str, Any]:
    """
    Convert currency from base currency to target currency using exchange rates from currencies.csv.
    """
    base = base_currency.strip().upper()
    target = target_currency.strip().upper()
    amt = float(amount)
    
    if base == target:
        return {
            "base_currency": base,
            "target_currency": target,
            "original_amount": amt,
            "converted_amount": amt,
            "exchange_rate": 1.0
        }
        
    if os.path.exists(CURRENCIES_CSV):
        with open(CURRENCIES_CSV, mode="r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if (row["base_currency"].strip().upper() == base and 
                    row["target_currency"].strip().upper() == target):
                    rate = float(row["exchange_rate"])
                    return {
                        "base_currency": base,
                        "target_currency": target,
                        "original_amount": amt,
                        "converted_amount": round(amt * rate, 2),
                        "exchange_rate": rate
                    }
                    
    # Fallback default
    return {
        "base_currency": base,
        "target_currency": target,
        "original_amount": amt,
        "converted_amount": amt,
        "exchange_rate": 1.0
    }

def get_current_time(timezone: str = "UTC") -> Dict[str, Any]:
    """
    Get current date and time for a given IANA timezone.
    Returns dict with datetime, timezone, date, time fields.
    """
    tz = None
    try:
        from zoneinfo import ZoneInfo
        tz = ZoneInfo(timezone)
    except Exception:
        tz = None
    now = datetime.now(tz)
    return {
        "datetime": now.isoformat(),
        "timezone": timezone,
        "date": now.strftime("%Y-%m-%d"),
        "time": now.strftime("%H:%M:%S")
    }

def check_visa_requirements(passport_nationality: str, destination_country: str) -> Dict[str, Any]:
    """
    Verify visa requirements for passport holder of a given nationality to destination country.
    """
    nat = passport_nationality.strip().lower()
    dest = destination_country.strip().lower()
    
    # Handle common nationality names
    if nat == "vietnamese":
        nat = "vietnam"
    elif nat == "american":
        nat = "us"
        
    if os.path.exists(VISA_CSV):
        with open(VISA_CSV, mode="r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                row_nat = row["passport_nationality"].strip().lower()
                row_dest = row["destination_country"].strip().lower()
                if row_nat == nat and row_dest == dest:
                    return {
                        "visa_required": row["visa_required"].strip().lower() == "true",
                        "max_stay_days": int(row["max_stay_days"]),
                        "notes": row["notes"].strip()
                    }
                    
    # Fallback default
    return {
        "visa_required": True,
        "max_stay_days": 30,
        "notes": f"Standard tourist visa is generally required for {passport_nationality} citizens traveling to {destination_country}."
    }
def get_airport_transfer(city: str, transfer_type: str = "all") -> Dict[str, Any]:
    TRANSFER_DB = {
        "tokyo": {
            "train": {"description": "Narita Express (N'EX)", "price_local": "¥3,070", "price_usd": 20.0, "duration_min": 53, "notes": "To Shinjuku. Runs every 30 min 07:00–21:30."},
            "bus":   {"description": "Airport Limousine Bus", "price_local": "¥3,200", "price_usd": 21.0, "duration_min": 75, "notes": "To major hotels. Runs 06:00–23:00."},
            "taxi":  {"description": "Fixed-rate taxi", "price_local": "¥20,000–30,000", "price_usd": 167.0, "duration_min": 75, "notes": "60–90 min depending on traffic."},
        },
        "singapore": {
            "train": {"description": "MRT East-West Line", "price_local": "SGD $2.50", "price_usd": 1.9, "duration_min": 30, "notes": "To City Hall. Runs 05:30–23:00."},
            "bus":   {"description": "Bus 36", "price_local": "SGD $2.10", "price_usd": 1.6, "duration_min": 60, "notes": "To Orchard Road. Runs 06:00–00:30."},
            "taxi":  {"description": "Metered taxi", "price_local": "SGD $20–35", "price_usd": 20.0, "duration_min": 30, "notes": "20–40 min. Airport surcharge applies."},
        },
        "hanoi": {
            "train": {"description": "No direct rail", "price_local": "N/A", "price_usd": 0.0, "duration_min": 0, "notes": "Airport Express Train (Cat Linh line connection) not yet available at Noi Bai."},
            "bus":   {"description": "Bus 86 (express)", "price_local": "45,000 VND", "price_usd": 1.8, "duration_min": 52, "notes": "To Old Quarter. Runs 05:05–22:30."},
            "taxi":  {"description": "Metered taxi (G7/Vinasun recommended)", "price_local": "250,000–400,000 VND", "price_usd": 13.0, "duration_min": 45, "notes": "40–50 min."},
        },
        "seoul": {
            "train": {"description": "AREX Express", "price_local": "KRW 9,500", "price_usd": 7.2, "duration_min": 43, "notes": "To Seoul Station. Runs 05:20–22:40."},
            "bus":   {"description": "Airport Limousine Bus", "price_local": "KRW 10,000–18,000", "price_usd": 10.6, "duration_min": 75, "notes": "To major areas. 60–90 min."},
            "taxi":  {"description": "Deluxe taxi", "price_local": "KRW 65,000–90,000", "price_usd": 58.0, "duration_min": 70, "notes": "60–80 min depending on destination."},
        },
        "bangkok": {
            "train": {"description": "Suvarnabhumi Airport Rail Link", "price_local": "THB 45", "price_usd": 1.28, "duration_min": 26, "notes": "To Phaya Thai BTS. Runs 06:00–00:00."},
            "bus":   {"description": "Public bus S1/S2", "price_local": "THB 60", "price_usd": 1.7, "duration_min": 75, "notes": "To city centre. Runs 05:00–20:00."},
            "taxi":  {"description": "Metered taxi + expressway tolls", "price_local": "THB 350–600", "price_usd": 13.0, "duration_min": 45, "notes": "30–60 min."},
        },
    }

    city_key = city.strip().lower()
    transfer_key = transfer_type.strip().lower()

    city_data = TRANSFER_DB.get(city_key)
    if not city_data:
        return {
            "city": city,
            "transfer_type": transfer_type,
            "options": {},
            "error": f"No airport transfer data for '{city}'. Supported cities: Tokyo, Singapore, Hanoi, Seoul, Bangkok."
        }

    if transfer_key == "all":
        return {
            "city": city,
            "transfer_type": "all",
            "options": city_data
        }

    if transfer_key in city_data:
        return {
            "city": city,
            "transfer_type": transfer_key,
            "options": {transfer_key: city_data[transfer_key]}
        }

    return {
        "city": city,
        "transfer_type": transfer_type,
        "options": {},
        "error": f"Transfer type '{transfer_type}' not recognised. Use: train, bus, taxi, or all."
    }
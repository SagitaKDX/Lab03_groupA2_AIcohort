"""Mock tool implementations for Travel Finder ReAct Agent.

Defines:
- search_flights
- hotel
- get_weather
- calculate_total_price
"""

import logging

logger = logging.getLogger(__name__)

# Mock Databases
_FLIGHTS_DB = {
    ("hà nội", "đà nẵng", "2025-06-20"): [
        {"flight_id": "VJ456", "price": 800000},
        {"flight_id": "VN123", "price": 1200000}
    ],
    ("hanoi", "da nang", "2025-06-20"): [
        {"flight_id": "VJ456", "price": 800000},
        {"flight_id": "VN123", "price": 1200000}
    ],
    ("hà nội", "đà nẵng", "2025-06-21"): [
        {"flight_id": "VJ457", "price": 850000},
    ],
    ("hà nội", "đà nẵng", "2025-06-19"): [
        {"flight_id": "VJ455", "price": 750000},
    ]
}

_HOTELS_DB = {
    ("đà nẵng", "budget"): [{"hotel_id": "HTL_001", "price": 500000}],
    ("da nang", "budget"): [{"hotel_id": "HTL_001", "price": 500000}],
    ("đà nẵng", "mid"): [
        {"hotel_id": "HTL_012", "price": 600000},
        {"hotel_id": "HTL_008", "price": 750000}
    ],
    ("da nang", "mid"): [
        {"hotel_id": "HTL_012", "price": 600000},
        {"hotel_id": "HTL_008", "price": 750000}
    ],
    ("đà nẵng", "luxury"): [{"hotel_id": "HTL_002", "price": 1500000}],
    ("da nang", "luxury"): [{"hotel_id": "HTL_002", "price": 1500000}],
}

_WEATHER_DB = {
    ("đà nẵng", "2025-06-20"): {"temp": 34, "rain_prob": 0.80},
    ("da nang", "2025-06-20"): {"temp": 34, "rain_prob": 0.80},
    ("đà nẵng", "2025-06-19"): {"temp": 32, "rain_prob": 0.15},
    ("đà nẵng", "2025-06-21"): {"temp": 33, "rain_prob": 0.20},
    ("đà nẵng", "2025-06-25"): {"temp": 31, "rain_prob": 0.10},
}


def get_weather(destination_city: str, departure_date: str) -> dict:
    """Kiểm tra thời tiết tại điểm đến vào ngày khởi hành.

    Args:
        destination_city: Tên thành phố điểm đến (ví dụ: "Đà Nẵng", "Sài Gòn").
        departure_date: Ngày khởi hành định dạng YYYY-MM-DD.

    Returns:
        Thông tin thời tiết gồm nhiệt độ (temp), xác suất mưa (rain_prob).
    """
    city_key = destination_city.lower().strip()
    date_key = departure_date.strip()

    # Giả lập check date quá xa (> 14 ngày kể từ 2026-06-01 hoặc mốc tượng trưng)
    if not date_key.startswith("2025-06"):
        return {"temp": None, "rain_prob": None, "note": "forecast_unavailable"}

    return _WEATHER_DB.get(
        (city_key, date_key),
        {"temp": 28, "rain_prob": 0.20} # Default fallback
    )


def search_flights(departure_city: str, destination_city: str, departure_date: str) -> list[dict]:
    """Tìm kiếm chuyến bay theo tuyến đường và ngày khởi hành.

    Args:
        departure_city: Thành phố đi (ví dụ: "Hà Nội").
        destination_city: Thành phố đến (ví dụ: "Đà Nẵng").
        departure_date: Ngày khởi hành định dạng YYYY-MM-DD.

    Returns:
        Danh sách chuyến bay và giá vé, hoặc [] nếu không tìm thấy.
    """
    dep_key = departure_city.lower().strip()
    dest_key = destination_city.lower().strip()
    date_key = departure_date.strip()

    if date_key < "2025-06-01":
        return {"error": "past_date"}

    return _FLIGHTS_DB.get((dep_key, dest_key, date_key), [])


def hotel(destination_city: str, rate: str) -> list[dict]:
    """Tìm kiếm khách sạn tại điểm đến theo phân khúc giá (rate).

    Args:
        destination_city: Tên thành phố cần tìm khách sạn.
        rate: Phân khúc giá, gồm "budget" (bình dân), "mid" (trung bình), "luxury" (cao cấp).

    Returns:
        Danh sách khách sạn phù hợp.
    """
    city_key = destination_city.lower().strip()
    rate_key = rate.lower().strip()

    if city_key not in ["đà nẵng", "da nang"]:
        return {"error": "city_not_found"}

    result = _HOTELS_DB.get((city_key, rate_key))
    if not result:
        # Fallback adjacent rate
        if rate_key == "luxury":
            result = _HOTELS_DB.get((city_key, "mid"))
        elif rate_key == "budget":
            result = _HOTELS_DB.get((city_key, "mid"))
        else:
            result = _HOTELS_DB.get((city_key, "budget"))

    return result or []


def calculate_total_price(flight_id: str, hotel_id: str) -> dict:
    """Tính tổng chi phí chuyến đi từ thông tin chuyến bay và phòng khách sạn đã chọn.

    Args:
        flight_id: Mã định danh của chuyến bay (ví dụ: "VJ456").
        hotel_id: Mã định danh của khách sạn (ví dụ: "HTL_012").

    Returns:
        Chi tiết chi phí chuyến bay, khách sạn và tổng tiền.
    """
    # Find flight price from DB mock
    flight_price = None
    for flights in _FLIGHTS_DB.values():
        for f in flights:
            if f["flight_id"] == flight_id:
                flight_price = f["price"]
                break
        if flight_price is not None:
            break

    # Find hotel price from DB mock
    hotel_price = None
    for hotels in _HOTELS_DB.values():
        for h in hotels:
            if h["hotel_id"] == hotel_id:
                hotel_price = h["price"]
                break
        if hotel_price is not None:
            break

    if flight_price is None or hotel_price is None:
        return {"error": "id_not_found"}

    return {
        "flight_price": flight_price,
        "hotel_price": hotel_price,
        "total": flight_price + hotel_price
    }


# Export details for tools array initialization
ALL_TOOLS = [
    {
        "name": "get_weather",
        "description": "Kiểm tra thời tiết tại điểm đến vào ngày khởi hành. Args: destination_city: str, departure_date: str (YYYY-MM-DD). Returns: {temp, rain_prob}.",
        "func": get_weather
    },
    {
        "name": "search_flights",
        "description": "Tìm kiếm chuyến bay theo tuyến đường và ngày khởi hành. Args: departure_city: str, destination_city: str, departure_date: str (YYYY-MM-DD). Returns list of flights.",
        "func": search_flights
    },
    {
        "name": "hotel",
        "description": "Tìm kiếm khách sạn tại điểm đến theo phân khúc giá (rate). Args: destination_city: str, rate: 'budget'|'mid'|'luxury'. Returns list of hotels.",
        "func": hotel
    },
    {
        "name": "calculate_total_price",
        "description": "Tính tổng chi phí chuyến đi từ thông tin chuyến bay và phòng khách sạn đã chọn. Args: flight_id: str, hotel_id: str. Returns dict with totals.",
        "func": calculate_total_price
    }
]

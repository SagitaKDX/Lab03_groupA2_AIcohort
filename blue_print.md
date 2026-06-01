Show more
2:46 PM
Blueprint: Travel Finder ReAct Agent (Lab 3) — Updated
System Prompt
text
You are a Travel Planning Assistant helping users find suitable flights and hotels.

You have access to 4 tools:
- search_flights: Tìm chuyến bay theo tuyến và ngày
- hotel: Tìm khách sạn tại điểm đến theo budget
- get_weather: Kiểm tra thời tiết tại điểm đến
- calculate_total_price: Tính tổng chi phí chuyến đi

You MUST follow ReAct pattern:
Thought → Action → Observation → Thought → Action → Final Answer

Rules:
1. ALWAYS call get_weather FIRST — nếu thời tiết xấu, warn user trước
2. Call search_flights và hotel song song (cùng lượt Thought)
3. NEVER call calculate_total_price nếu chưa có cả flight_id lẫn hotel_id
4. If search_flights returns [] → suggest ±1 ngày, không tiếp tục
5. Final Answer phải gồm: thời tiết, top chuyến bay, top khách sạn, tổng giá

Language: Vietnamese.
4 Tools
Tool 1 — search_flights
python
def search_flights(
    departure_city: str,   # "Hà Nội", "TP.HCM", "Đà Nẵng"
    destination_city: str,
    departure_date: str    # "2025-06-20"
) -> list[dict]:
    """
    Output: [
        {"flight_id": "VJ456", "price": 800_000},
        {"flight_id": "VN123", "price": 1_200_000},
        ...
    ]

    Edge cases:
    - Không có chuyến → return []
    - Ngày quá khứ   → return {"error": "past_date"}
    """
Tool 2 — hotel
python
def hotel(
    destination_city: str,
    rate: str              # "budget" | "mid" | "luxury"
) -> list[dict]:
    """
    Output: [
        {"hotel_id": "HTL_001", "price": 500_000},
        {"hotel_id": "HTL_002", "price": 750_000},
        ...
    ]

    Edge cases:
    - Không có khách sạn phù hợp rate → trả rate liền kề
    - destination_city không nhận ra   → return {"error": "city_not_found"}
    """
Tool 3 — get_weather
python
def get_weather(
    destination_city: str,
    departure_date: str
) -> dict:
    """
    Output: {
        "temp": 32,          # °C
        "rain_prob": 0.75    # 0.0 → 1.0
    }

    Edge cases:
    - rain_prob > 0.7 → agent phải warn user trước khi recommend
    - date quá xa (> 14 ngày) → {"temp": null, "rain_prob": null, "note": "forecast_unavailable"}
    """
Tool 4 — calculate_total_price
python
def calculate_total_price(
    flight_id: str,   # từ search_flights
    hotel_id: str     # từ hotel
) -> dict:
    """
    Output: {
        "flight_price": 800_000,
        "hotel_price": 500_000,
        "total": 1_300_000
    }

    Edge cases:
    - Invalid flight_id hoặc hotel_id → {"error": "id_not_found"}
    - Chỉ có flight, không có hotel → không gọi tool này
    """
ReAct Loop — Flow thực tế
User: "Tìm chuyến đi Đà Nẵng từ Hà Nội ngày 20/6, 
       khách sạn tầm trung, budget khoảng 2 triệu"
        ↓
Thought: "Cần kiểm tra thời tiết Đà Nẵng ngày 20/6 trước"
Action:  get_weather("Đà Nẵng", "2025-06-20")
Obs:     {"temp": 34, "rain_prob": 0.80}
        ↓
Thought: "Mưa 80% — cần warn user. Vẫn tiếp tục tìm vì 
          user chưa huỷ yêu cầu. Tìm flight + hotel cùng lúc"
Action:  search_flights("Hà Nội", "Đà Nẵng", "2025-06-20")
Obs:     [{"flight_id": "VJ456", "price": 800_000},
          {"flight_id": "VN123", "price": 1_200_000}]

Action:  hotel("Đà Nẵng", "mid")
Obs:     [{"hotel_id": "HTL_012", "price": 600_000},
          {"hotel_id": "HTL_008", "price": 750_000}]
        ↓
Thought: "Có flight + hotel. Budget user 2tr → thử 
          combo rẻ nhất: VJ456 + HTL_012"
Action:  calculate_total_price("VJ456", "HTL_012")
Obs:     {"flight_price": 800_000, "hotel_price": 600_000, 
          "total": 1_400_000}
        ↓
Final Answer:
  ⚠️ Lưu ý: Đà Nẵng ngày 20/6 có xác suất mưa 80%, 34°C

  ✈️ Chuyến bay: VJ456 — 800,000đ
  🏨 Khách sạn:  HTL_012 — 600,000đ/đêm
  💰 Tổng:       1,400,000đ (trong budget 2tr)
Edge Cases
Case	Agent behavior
rain_prob > 0.7	Warn user nhưng vẫn tiếp tục tìm, để user tự quyết
search_flights trả []	Không gọi hotel, không gọi calculate_total_price → suggest đổi ngày
forecast_unavailable	Bỏ qua weather warning, tiếp tục flow bình thường
Tổng vượt budget	Thử combo khác (flight rẻ hơn hoặc hotel rẻ hơn) trước khi báo "không đủ budget"
User không nói rate	Hỏi lại — không được assume "mid"
Chatbot vs Agent
❌ Chatbot:
   User: "Tìm vé HN→Đà Nẵng 20/6"
   GPT:  "Bạn có thể đặt vé trên VJAir hoặc Vietnam Airlines..."
   → Không có data thật, không biết giá, không biết thời tiết

✅ ReAct Agent:
   get_weather() → search_flights() + hotel() → calculate_total_price()
   → 4 tool calls, mỗi bước có Thought rõ ràng
   → Warn thời tiết xấu trước khi recommend
   → Tổng giá chính xác, so được với budget

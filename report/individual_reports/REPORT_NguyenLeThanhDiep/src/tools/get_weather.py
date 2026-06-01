import csv

# Biến cấu hình kịch bản lỗi giả lập khí tượng (cho get_weather)
SIMULATE_ERROR = False

def get_weather(destination_city: str, departure_date: str) -> dict:
    """Kiểm tra thời tiết tại điểm đến => temp, rain_prob"""
    # Bổ sung logic SIMULATE_ERROR để phục vụ bài giảng lỗi kết nối khí tượng
    if SIMULATE_ERROR:
        raise Exception(f"Connection timeout: Không thể kết nối đến trạm khí tượng tại {destination_city} (Lỗi giả lập live demo).")
        
    dest_city_clean = destination_city.strip().lower()
    dep_date_clean = departure_date.strip().lower()
    
    if "mai" in dep_date_clean or any(char.isdigit() for char in dep_date_clean):
        dep_date_clean = "ngày mai"
        
    import os
    csv_path = os.path.join(os.path.dirname(__file__), 'weather.csv')
    try:
        with open(csv_path, mode='r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if (row['destination_city'].strip().lower() == dest_city_clean and 
                    row['departure_date'].strip().lower() == dep_date_clean):
                    return {
                        "temp": int(row['temp']),
                        "rain_prob": float(row['rain_prob'])
                    }
    except Exception as e:
        print(f"Error reading weather.csv: {e}")
    
    # Fallback mặc định
    return {"temp": 25, "rain_prob": 0.5}

# Định nghĩa OpenAI Function Calling Schema cho get_weather
SCHEMA = {
    "type": "function",
    "function": {
        "name": "get_weather",
        "description": "Kiểm tra thời tiết tại điểm đến destination_city vào ngày khởi hành departure_date. Trả về nhiệt độ (temp) và xác suất mưa (rain_prob).",
        "parameters": {
            "type": "object",
            "properties": {
                "destination_city": {
                    "type": "string",
                    "description": "Thành phố điểm đến cần kiểm tra thời tiết."
                },
                "departure_date": {
                    "type": "string",
                    "description": "Ngày kiểm tra thời tiết."
                }
            },
            "required": ["destination_city", "departure_date"]
        }
    }
}

import csv

def search_flights(departure_city: str, destination_city: str, departure_date: str) -> list:
    """Tìm danh sách chuyến bay phù hợp từ file csv => flight_id, price"""
    results = []
    
    # Chuẩn hóa đầu vào để tăng độ chịu lỗi (Fault tolerance)
    dep_city_clean = departure_city.strip().lower()
    dest_city_clean = destination_city.strip().lower()
    dep_date_clean = departure_date.strip().lower()
    
    # Nếu LLM truyền ngày dạng YYYY-MM-DD hoặc bất kỳ ngày nào, ta tự động ánh xạ về dữ liệu mock "ngày mai"
    if "mai" in dep_date_clean or any(char.isdigit() for char in dep_date_clean):
        dep_date_clean = "ngày mai"
        
    import os
    csv_path = os.path.join(os.path.dirname(__file__), 'flights.csv')
    try:
        with open(csv_path, mode='r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if (row['departure_city'].strip().lower() == dep_city_clean and 
                    row['destination_city'].strip().lower() == dest_city_clean and 
                    row['departure_date'].strip().lower() == dep_date_clean):
                    results.append({
                        "flight_id": row['flight_id'],
                        "price": int(row['price'])
                    })
    except Exception as e:
        print(f"Error reading flights.csv: {e}")
    return results

# Định nghĩa OpenAI Function Calling Schema cho search_flights
SCHEMA = {
    "type": "function",
    "function": {
        "name": "search_flights",
        "description": "Tìm danh sách các chuyến bay phù hợp đi từ departure_city tới destination_city vào ngày departure_date. Trả về danh sách chứa các chuyến bay gồm flight_id và price.",
        "parameters": {
            "type": "object",
            "properties": {
                "departure_city": {
                    "type": "string",
                    "description": "Thành phố khởi hành (ví dụ: Hà Nội)."
                },
                "destination_city": {
                    "type": "string",
                    "description": "Thành phố điểm đến (ví dụ: Paris, TP HCM)."
                },
                "departure_date": {
                    "type": "string",
                    "description": "Ngày khởi hành chuyến bay (ví dụ: ngày mai)."
                }
            },
            "required": ["departure_city", "destination_city", "departure_date"]
        }
    }
}

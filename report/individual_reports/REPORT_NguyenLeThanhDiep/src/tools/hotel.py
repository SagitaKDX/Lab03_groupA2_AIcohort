import csv

def hotel(destination_city: str, rate: int) -> list:
    """Tìm khách sạn phù hợp tại điểm đến theo số sao => hotel_id, price"""
    results = []
    dest_city_clean = destination_city.strip().lower()
    
    import os
    csv_path = os.path.join(os.path.dirname(__file__), 'hotels.csv')
    try:
        with open(csv_path, mode='r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if (row['destination_city'].strip().lower() == dest_city_clean and 
                    int(row['rate']) == int(rate)):
                    results.append({
                        "hotel_id": row['hotel_id'],
                        "price": int(row['price'])
                    })
    except Exception as e:
        print(f"Error reading hotels.csv: {e}")
    return results

# Định nghĩa OpenAI Function Calling Schema cho hotel
SCHEMA = {
    "type": "function",
    "function": {
        "name": "hotel",
        "description": "Tìm danh sách các khách sạn tại destination_city phù hợp với số sao rate (ví dụ: 4 hoặc 5 sao). Trả về danh sách chứa hotel_id và price.",
        "parameters": {
            "type": "object",
            "properties": {
                "destination_city": {
                    "type": "string",
                    "description": "Thành phố điểm đến (ví dụ: Paris, TP HCM)."
                },
                "rate": {
                    "type": "integer",
                    "description": "Đánh giá xếp hạng số sao của khách sạn (ví dụ: 4 hoặc 5)."
                }
            },
            "required": ["destination_city", "rate"]
        }
    }
}

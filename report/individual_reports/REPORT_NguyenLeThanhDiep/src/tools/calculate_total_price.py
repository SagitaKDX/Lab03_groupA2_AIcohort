import csv

def calculate_total_price(flight_id: str, hotel_id: str) -> dict:
    """Tính tổng giá tiền chuyến đi dựa trên mã chuyến bay và mã khách sạn => total_price"""
    flight_price = 0
    hotel_price = 0
    
    f_id_clean = flight_id.strip().upper()
    h_id_clean = hotel_id.strip().upper()
    
    import os
    # Tra cứu giá chuyến bay
    flights_csv = os.path.join(os.path.dirname(__file__), 'flights.csv')
    try:
        with open(flights_csv, mode='r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row['flight_id'].strip().upper() == f_id_clean:
                    flight_price = int(row['price'])
                    break
    except Exception as e:
        print(f"Error searching flight price: {e}")
        
    # Tra cứu giá khách sạn
    hotels_csv = os.path.join(os.path.dirname(__file__), 'hotels.csv')
    try:
        with open(hotels_csv, mode='r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row['hotel_id'].strip().upper() == h_id_clean:
                    hotel_price = int(row['price'])
                    break
    except Exception as e:
        print(f"Error searching hotel price: {e}")
        
    return {
        "flight_id": flight_id,
        "hotel_id": hotel_id,
        "flight_price": flight_price,
        "hotel_price": hotel_price,
        "total_price": flight_price + hotel_price
    }

# Định nghĩa OpenAI Function Calling Schema cho calculate_total_price
SCHEMA = {
    "type": "function",
    "function": {
        "name": "calculate_total_price",
        "description": "Tính toán tổng chi phí của chuyến đi dựa trên flight_id và hotel_id được chọn từ các bước trước. Trả về chi tiết và tổng giá tiền total_price.",
        "parameters": {
            "type": "object",
            "properties": {
                "flight_id": {
                    "type": "string",
                    "description": "Mã chuyến bay được lựa chọn từ kết quả search_flights."
                },
                "hotel_id": {
                    "type": "string",
                    "description": "Mã khách sạn được lựa chọn từ kết quả hotel."
                }
            },
            "required": ["flight_id", "hotel_id"]
        }
    }
}

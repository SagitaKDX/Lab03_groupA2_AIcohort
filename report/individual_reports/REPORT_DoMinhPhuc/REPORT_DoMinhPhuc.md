# Individual Report: Lab 3 - Chatbot vs ReAct Agent

* **Student Name**: Đỗ Minh Phúc
* **Student ID**: 2A202600585
* **Date**: 2026-06-01

---

## I. Technical Contribution (15 Points)

* **Modules Implemented**:
  * Codebase nhóm: Thiết lập tool cho agent tìm kiếm thông tin các phương tiện di chuyển từ sân bay
  * `src/agent/agent.py`: Thiết lập cấu trúc cốt lõi cho ReAct Agent bao gồm vòng lặp suy luận (Thought → Action → Observation), cơ chế tự động xây dựng tài liệu công cụ (`_build_tool_docs`) từ signature của hàm, quản lý lịch sử hội thoại (`_build_prompt`), và xử lý bóc tách dữ liệu JSON nghiêm ngặt (`_parse_json`).
  * `src/agent/tools.py`: Triển khai các công cụ thực thi (tools) mô phỏng database để Agent tương tác bao gồm: tra cứu chuyến bay (`search_flights`), tra cứu phòng khách sạn (`search_hotel`), dự báo thời tiết (`get_weather`), và hàm xử lý logic tính toán tổng chi phí cuối cùng kèm thuế (`calculate_total_price`).
  * `src/telemetry/logger.py` & `src/telemetry/metrics.py`: Xây dựng hệ thống giám sát và đo lường hiệu suất chuẩn công nghiệp. `logger.py` xử lý ghi log có cấu trúc dưới định dạng JSON. `metrics.py` quản lý lớp `PerformanceTracker` để tính toán chi phí tài chính (USD) và token.
  * `src/agent/chatbot.py`: Triển khai module Chatbot truyền thống làm môi trường đối chứng (baseline).

* **Code Highlights**:
  * **Cơ chế bóc tách và chuẩn hóa JSON (`src/agent/agent.py`):** Dùng Regex làm sạch ký tự markdown của LLM để tránh crash hệ thống:
~~~python
def _parse_json(raw: str) -> dict:
    """Strip ``` fences, then extract outermost { ... }"""
    text = re.sub(r"
http://googleusercontent.com/immersive_entry_chip/0
~~~
* **Diagnosis**: Khi người dùng yêu cầu "calculate the total cost with 10% tax", LLM (Mô hình) có xu hướng hiểu nhầm giá trị "10" là số nguyên và gán thẳng vào `action_input: {"tax_rate": 10}`. Điều này vi phạm khối lệnh kiểm tra `0.0 <= tax_rate <= 1.0` được thiết kế chặt chẽ trong file `tools.py`.
* **Solution**: Để khắc phục, em đã cập nhật biến `SYSTEM_PROMPT` trong file `agent.py`, thêm một khối quy tắc nhấn mạnh (CRITICAL RULES) để ép LLM tuân thủ định dạng: `tax_rate must be a decimal: 0.10 means 10%, NEVER pass 10`.

---

---

## II. Debugging Case Study (10 Points)

* **Problem Description**: Agent bị vướng lỗi khi gọi công cụ `calculate_total_price` do truyền sai tham số thuế suất (`tax_rate`). Thay vì truyền số thập phân, LLM truyền số nguyên, khiến tool báo lỗi từ chối thực thi.
* **Log Source**: Trích xuất từ file log `logs/2026-06-01.log`:
~~~json
{"timestamp": "2026-06-01T15:30:22.105", "event": "TOOL_ERROR", "data": {"step": 4, "tool": "calculate_total_price", "error": "Error: tax_rate must be 0.0–1.0 (e.g. 0.10 for 10%), got 10"}}
~~~
* **Diagnosis**: Khi người dùng yêu cầu "calculate the total cost with 10% tax", LLM (Mô hình ngôn ngữ) có xu hướng hiểu nhầm giá trị "10" là số nguyên và gán thẳng vào `action_input: {"tax_rate": 10}`. Điều này vi phạm khối lệnh kiểm tra `0.0 <= tax_rate <= 1.0` được thiết kế chặt chẽ trong file `tools.py`.
* **Solution**: Để khắc phục, tôi đã cập nhật biến `SYSTEM_PROMPT` trong file `agent.py`, thêm một khối quy tắc nhấn mạnh (CRITICAL RULES) để ép LLM tuân thủ định dạng: `tax_rate must be a decimal: 0.10 means 10%, NEVER pass 10`.

---

## III. Personal Insights: Chatbot vs ReAct (10 Points)

*Reflect on the reasoning capability difference.*

1. **Reasoning**: Khối `Thought` giúp Agent chia nhỏ bài toán phức tạp thành các bước rõ ràng. Thay vì cố gắng trả lời ngay và bịa số liệu (hallucination) như Chatbot truyền thống, ReAct Agent tư duy tuần tự: Tìm chuyến bay rẻ nhất $\rightarrow$ Tìm khách sạn $\rightarrow$ Lấy thông tin thời tiết $\rightarrow$ Tính toán tổng tiền. 
2. **Reliability**: Agent hoạt động **tệ hơn** Chatbot trong những trường hợp câu hỏi quá đơn giản không cần công cụ, do Agent tiêu tốn nhiều token/chi phí hơn, độ trễ (latency) cao hơn, và đôi khi sinh ra chuỗi JSON sai cú pháp khiến vòng lặp bị dừng hoặc chạm ngưỡng timeout (`max_steps=10`).
3. **Observation**: Môi trường phản hồi (`Observation`) đóng vai trò là "nhận thức thực tế". Khi tool `search_flights` trả về giá vé là `$420.0`, con số này được nạp lại vào lịch sử. Ở bước tiếp theo, LLM lấy chính xác số `$420.0` này làm input cho tool `calculate_total_price` thay vì tự đoán một mức giá ngẫu nhiên, đảm bảo độ chính xác tuyệt đối.

---

## IV. Future Improvements (5 Points)

*How would you scale this for a production-level AI agent system?*

* **Scalability**: Áp dụng lập trình bất đồng bộ (`asyncio` trong Python) cho các tool. Trong môi trường production, việc gọi API bên ngoài (như hệ thống đặt vé máy bay thật) sẽ có độ trễ lớn. Async giúp hệ thống xử lý song song nhiều request của user mà không bị block thread.
* **Safety**: Cần triển khai một 'Supervisor LLM' (Mô hình giám sát) hoặc tính năng Human-in-the-loop. Đối với các hành động nhạy cảm như "thanh toán hóa đơn" hay "xóa database", hệ thống không được tự động chạy tool mà phải yêu cầu người dùng xác nhận (`Observation: Please confirm payment...`).
* **Performance**: Hiện tại biến `SYSTEM_PROMPT` nạp toàn bộ danh sách công cụ `TOOLS` vào ngữ cảnh. Với hệ thống lớn có hàng trăm tools, điều này làm cạn kiệt token và gây nhiễu cho LLM. Cải tiến bằng cách dùng Vector DB (RAG) để nhúng (embed) truy vấn của user, sau đó chỉ truy xuất (retrieve) Top-3 tools liên quan nhất nạp vào prompt.

---

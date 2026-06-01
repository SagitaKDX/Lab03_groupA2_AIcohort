# Individual Report: Lab 3 - Chatbot vs ReAct Agent

- **Student Name**: Nguyễn Lê Thanh Điệp
- **Student ID**: 2A202600636
- **Date**: 01/06/2026

---

## I. Technical Contribution (15 Points)

*Describe your specific contribution to the codebase (e.g., implemented a specific tool, fixed the parser, etc.).*

- **Modules Implementated**: Codebase nhóm: `server.py`,`web/app.js`,`web/index.html`,`style.css`. Implemented the API to get today's log file and display it in the web interface.
    * (REPORT_NguyenLeThanhDiep/src): tự thiết lập agent ReAct riêng phục vụ debug cá nhân. Có vòng lặp suy luận để đưa ra kết quả chuẩn nhất. Triển khai các hàm tool cơ bản để agent ReAct có thể tương tác với hệ thống để lấy data mô phỏng.

- **Code Highlights**: 
    + (https://github.com/SagitaKDX/Lab03_groupA2_AIcohort/blob/main/server.py#L151-L184): API Get today's log file 
    + (https://github.com/SagitaKDX/Lab03_groupA2_AIcohort/blob/main/web/app.js#406-L540): 
- **Documentation**: Debug logs are stored in the `logs` folder and can be viewed in the web interface. 

---

## II. Debugging Case Study (10 Points)

*Analyze a specific failure event you encountered during the lab using the logging system.*

- **Problem Description**: Agent bị loop vĩnh 
- **Log Source**: `logs/2026-06-01.log`
- **Diagnosis**: System Prompt không mô tả kĩ các hàm tool đã định nghĩa, vì thế hàm `convert_currency` là hàm định nghĩa, nhưng `convert_currency_vn` lại được gọi khiến bị loop. chứng tỏ LLM đã bị hallucination và không thể tự hiểu được.
- **Solution**: Đưa các định nghĩa hàm tool vào trong System Prompt sẽ fix đc lỗi của Hallucination

---

## III. Personal Insights: Chatbot vs ReAct (10 Points)

*Reflect on the reasoning capability difference.*

1.  **Reasoning**: Nó cho phép Agent có khả năng suy luận tốt hơn, đặc biệt là trong các tác vụ phức tạp yêu cầu nhiều bước. Chatbot thường chỉ trả lời dựa trên thông tin đã học, trong khi Agent có thể sử dụng các công cụ để thu thập thêm thông tin và đưa ra quyết định tốt hơn.
2.  **Reliability**: In which cases did the Agent actually perform *worse* than the Chatbot? Agent có thể gặp khó khăn khi phải xử lý các tác vụ yêu cầu sự sáng tạo cao. Trong những trường hợp này, Chatbot có thể trả lời nhanh hơn và chính xác hơn vì nó không phải lo lắng về việc chọn công cụ phù hợp.
3.  **Observation**: How did the environment feedback (observations) influence the next steps? Agent có thể sử dụng các quan sát để điều chỉnh chiến lược của mình. Ví dụ, nếu một công cụ không hoạt động như mong đợi, Agent có thể thử một công cụ khác hoặc thay đổi cách tiếp cận. Điều này giúp Agent trở nên linh hoạt hơn trong việc giải quyết vấn đề.

---

## IV. Future Improvements (5 Points)

*How would you scale this for a production-level AI agent system?*

- **Scalability**: Cải thiện tốc độ xử lí các request từ user. Hiện tại có độ trễ đáng kể khi xử lý các tác vụ phức tạp.
- **Safety**: Để đảm bảo an toàn, có thể triển khai một LLM giám sát để kiểm tra các hành động của Agent hoặc đưa Human-in-the-loop vào. Điều này sẽ giúp ngăn chặn các hành động không mong muốn hoặc có hại.
- **Performance**: Sử dụng một hệ thống cơ sở dữ liệu vector để lưu trữ và truy xuất các công cụ có thể giúp cải thiện hiệu suất khi có nhiều công cụ được định nghĩa. Điều này sẽ giúp Agent nhanh chóng tìm thấy công cụ phù hợp cho từng tác vụ mà không phải duyệt qua tất cả các công cụ một cách tuần tự.

---

> [!NOTE]
> Submit this report by renaming it to `REPORT_[YOUR_NAME].md` and placing it in this folder.

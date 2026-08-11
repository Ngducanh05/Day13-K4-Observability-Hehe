# Alert và Runbook

Các alert dưới đây bám vào triệu chứng/SLO mà người dùng cảm nhận được. Khi xử lý incident, luôn đi theo chuỗi **Metrics → Traces → Logs** và ghi lại trace ID/correlation ID làm evidence.

## Alert 1 — High Tail Latency

- **Tên:** `HighTailLatency`
- **Severity:** high
- **SLI/SLO liên quan:** `latency_p95_ms <= 3000 ms`
- **Điều kiện và thời gian duy trì:** P95 > 3000 ms liên tục 5 phút.
- **Ảnh hưởng tới người dùng:** câu trả lời AI chậm, timeout phía client hoặc trải nghiệm không ổn định.
- **Ba bước kiểm tra đầu tiên:**
  1. Mở panel Latency, xác nhận P50/P95/P99 và khoảng thời gian bắt đầu tăng.
  2. Mở một trace chậm trong cùng cửa sổ và tìm span chiếm phần lớn waterfall.
  3. Dùng correlation ID để tìm log `request_received` → `response_sent`/`request_failed`.
- **Mitigation tạm thời:** rollback thay đổi gần nhất; dùng fallback/caching; trong lab tắt incident sau khi đã lưu evidence.
- **Owner:** `sre-oncall`.

## Alert 2 — High Error Rate

- **Tên:** `HighErrorRate`
- **Severity:** critical
- **SLI/SLO liên quan:** `error_rate_pct <= 2%`
- **Điều kiện và thời gian duy trì:** error rate > 2% liên tục 5 phút.
- **Ảnh hưởng tới người dùng:** request `/chat` trả 5xx hoặc không có câu trả lời.
- **Ba bước kiểm tra đầu tiên:**
  1. Mở panel Errors và breakdown theo `error_type`.
  2. Chọn trace lỗi đại diện, xác định span/tool phát sinh exception.
  3. Tìm log cùng correlation ID và kiểm tra `request_failed.error_type`.
- **Mitigation tạm thời:** cô lập dependency lỗi, bật fallback, giảm retry storm, rollback bản phát hành gây lỗi.
- **Owner:** `sre-oncall`.

## Alert 3 — Cost Budget Burn

- **Tên:** `CostBudgetBurn`
- **Severity:** warning
- **SLI/SLO liên quan:** `daily_cost_usd <= 2.5`
- **Điều kiện và thời gian duy trì:** rolling 24h cost > 2.5 USD trong 15 phút.
- **Ảnh hưởng tới người dùng:** nguy cơ vượt ngân sách và buộc phải throttle hệ thống.
- **Ba bước kiểm tra đầu tiên:**
  1. So sánh Cost với Traffic để phân biệt volume tăng và cost/request tăng.
  2. Mở trace cost cao, kiểm tra prompt/completion tokens, model và prompt version.
  3. Tìm log cùng correlation ID, so sánh `tokens_in`, `tokens_out`, `cost_usd`, `feature`.
- **Mitigation tạm thời:** giới hạn output token, rollback prompt/model làm phình token, cache hoặc throttle feature không quan trọng.
- **Owner:** `ai-platform`.

## Sau incident

Cập nhật `submission/REPORT.md` bằng metric cụ thể, trace ID, correlation ID/log line, root cause, fix action và preventive measure. Không dùng evidence không thể kiểm chứng.

# Báo cáo Day 13 Observability

> Các trường `[RUNTIME EVIDENCE]` bắt buộc lấy sau khi chạy hệ thống/Langfuse. Không điền giả trace ID, screenshot hoặc commit SHA.

## 1. Thông tin nhóm

- Tên nhóm: Day13-K4-Observability-Hehe
- Repository URL: https://github.com/Ngducanh05/Day13-K4-Observability-Hehe
- Commit SHA cuối: `[RUNTIME EVIDENCE]`
- Thành viên và vai trò:
  - Nguyễn Hải Anh — Middleware / Correlation ID
  - Tô Ngọc Hải — PII / Redaction
  - Nông Ngọc Dương — Metrics / Dashboard
  - Nguyễn Đức Anh — SRE / SLO / Alert / Runbook
  - Lê Thị Hải Yến — QA / Checkpoint 3 / Incident evidence

## 2. Kết quả kỹ thuật

- Điểm `validate_logs.py`: `[RUNTIME EVIDENCE: mục tiêu >= 80/100]`
- Tổng số traces: `[RUNTIME EVIDENCE: tối thiểu 10]`
- Số PII leak còn lại: `[RUNTIME EVIDENCE: mục tiêu 0]`
- Kết quả `validate_dashboard.py`: `[RUNTIME EVIDENCE: HỢP LỆ 6/6 panel]`
- Dashboard evidence: `submission/evidence/[tên ảnh].png`

## 3. Logging và tracing

- Correlation ID: `req-<8-hex>`, bind bằng structlog ContextVars và trả qua `x-request-id`.
- Metadata: `user_id_hash`, `session_id`, `feature`, `model`, `env`.
- PII: scrub đệ quy trước khi JSON được ghi.
- Evidence correlation ID: `[RUNTIME EVIDENCE]`
- Evidence PII redaction: `[RUNTIME EVIDENCE]`
- Trace waterfall + trace ID: `[RUNTIME EVIDENCE]`
- Span đáng chú ý: `[RUNTIME EVIDENCE]`

## 4. Prompt versioning

- Prompt name: `day13-chat`
- Baseline: v1, labels `baseline` + `production`
- Candidate: v2, label `candidate`
- Trace ID baseline: `[RUNTIME EVIDENCE]`
- Trace ID candidate: `[RUNTIME EVIDENCE]`
- Bằng chứng đổi label/rollback: `[RUNTIME EVIDENCE]`

## 5. Dashboard, SLO và alerts

Dashboard gồm đúng 6 panel: latency, traffic, errors, cost, tokens, quality.

SLO 28 ngày:
- P95 latency <= 3000 ms.
- Error rate <= 2%.
- Daily cost <= 2.5 USD.
- Average quality >= 0.75.

Alerts:
- `HighTailLatency`: P95 > 3000 ms trong 5 phút.
- `HighErrorRate`: error rate > 2% trong 5 phút.
- `CostBudgetBurn`: daily cost > 2.5 USD trong 15 phút.
- Runbook: `docs/alerts.md`.

## 6. Điều tra challenge K4

- Challenge ID: `day13-k4-observability-v1`
- Incident: `rag_slow`
- Affected feature: `monitoring`
- Threshold: `2000 ms`
- Triệu chứng metric thực tế: `[RUNTIME EVIDENCE]`
- Trace ID: `[RUNTIME EVIDENCE]`
- Correlation ID/log line: `[RUNTIME EVIDENCE]`

### Giả thuyết root cause cần xác nhận

Khi `rag_slow` bật, source retrieval cố ý chờ khoảng 2.5 giây. Vì threshold challenge là 2 giây, cần dùng trace waterfall và log cùng correlation ID để xác nhận retrieval span là nguyên nhân tail latency tăng.

### Fix action

- Tắt incident sau khi thu thập evidence.
- Với production: timeout/budget cho retrieval, caching, tối ưu query/datastore, kiểm soát retry.

### Preventive measure

- Alert tail latency theo P95/P99.
- Span riêng cho retrieval.
- Load/regression test tail latency.
- Runbook Metrics → Traces → Logs.

## 7. Đóng góp cá nhân

| Thành viên | Phần việc | Commit/PR | Điều đã học |
|---|---|---|---|
| `[Nguyễn Hải Anh-2A202601670]` | Middleware/correlation | `[commit/PR]` | ContextVars |
| `[Tô Ngọc Hải-2A202601686]` | PII/redaction | `[commit/PR]` | Privacy |
| `[Nông Ngọc Dương-2A202601296]` | Metrics/dashboard | `[commit/PR]` | Percentile/SLI |
| `[Nguyễn Đức Anh-2A202601870]` | SLO/alert/runbook | `[commit/PR]` | SRE |
| `[Lê Thị Hải Yến-2A202601570]` | QA/CP3 | `[commit/PR]` | Incident evidence |

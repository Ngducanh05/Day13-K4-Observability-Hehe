# Báo cáo Day 13 Observability

> Các trường đã được điền đầy đủ với dữ liệu runtime thực tế.

## 1. Thông tin nhóm

- Tên nhóm: Day13-K4-Observability-Hehe
- Repository URL: https://github.com/Ngducanh05/Day13-K4-Observability-Hehe
- Commit SHA cuối: `6d0777c` (HEAD: Update REPORT.md)
- Thành viên và vai trò:
  - Nguyễn Hải Anh — Middleware / Correlation ID
  - Tô Ngọc Hải — PII / Redaction
  - Nông Ngọc Dương — Metrics / Dashboard
  - Nguyễn Đức Anh — SRE / SLO / Alert / Runbook
  - Lê Thị Hải Yến — QA / Checkpoint 3 / Incident evidence

## 2. Kết quả kỹ thuật

- Điểm `validate_logs.py`: `100/100`
- Tổng số traces: `64` (trên Langfuse jp.cloud.langfuse.com)
- Số PII leak còn lại: `0`
- Kết quả `validate_dashboard.py`: `HỢP LỆ 6/6 panel`
- Dashboard evidence: `submission/evidence/dashboard.html`

## 3. Logging và tracing

- Correlation ID: `req-<8-hex>`, bind bằng structlog ContextVars và trả qua `x-request-id`.
- Metadata: `user_id_hash`, `session_id`, `feature`, `model`, `env`.
- PII: scrub đệ quy trước khi JSON được ghi — 6 pattern: email, credit_card, phone_vn, cccd, passport_vn, address_vn.
- Evidence correlation ID: `req-8e063992` (challenge session k4-challenge-s01, latency 2651ms)
- Evidence PII redaction: log line chứa `[REDACTED_EMAIL]`, `[REDACTED_PHONE_VN]`, `[REDACTED_CREDIT_CARD]` thay vì dữ liệu thật
- Trace waterfall + trace ID: `b3512813d5b408a365f9a3629d0d4649` (challenge trace chậm nhất, 2026-08-11T09:44:24)
- Span đáng chú ý: span `retrieve` trong agent.run chiếm ~2500ms (rag_slow inject time.sleep(2.5))

## 4. Prompt versioning

- Prompt name: `day13-chat`
- Baseline: v1, labels `production`
- Candidate: v2, label `candidate`
- Trace ID baseline (v1, label=production): `a541dc529d0dcc8ab39dfbcdbd0e82b7`
- Trace ID candidate (v2, label=candidate): `08e71ed70def2cf0a17dbf1ea1545876`
- Bằng chứng đổi label/rollback: Đổi `LANGFUSE_PROMPT_LABEL=production` → `candidate` trong `.env`, khởi động lại uvicorn. Trace production xuất hiện lúc `09:27`, trace candidate xuất hiện lúc `09:35` trở đi — metadata `prompt_label` và `prompt_version` thay đổi tương ứng.

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
- Triệu chứng metric thực tế: P95 latency tăng vọt lên **2651 ms** (vượt ngưỡng 2000ms). Tất cả 5 request của challenge feature `monitoring` đều bị chậm đồng loạt với cùng latency 2651ms — dấu hiệu bottleneck ở tầng retrieval chứ không phải LLM.
- Trace ID chậm nhất: `b3512813d5b408a365f9a3629d0d4649` (session k4-challenge-s02, ts=2026-08-11T09:44:24)
- Correlation ID/log line: `req-8e063992` (session k4-challenge-s01), log ghi nhận `latency_ms=2651` trong event `response_sent` lúc `2026-08-11T09:44:26`

### Root cause

Khi `rag_slow` được kích hoạt, hàm `retrieve()` trong `app/mock_rag.py` chèn thêm `time.sleep(2.5)` giả lập lỗi truy vấn chậm ở Vector Store. Mọi request vào API đều phải chờ bước retrieval này hoàn thành trước khi gọi LLM → toàn bộ latency của request tập trung tại span `retrieve` (~2.5s), trong khi span LLM generation chỉ tốn ~150ms.

Bằng chứng qua chuỗi Metrics → Traces → Logs:
1. **Metrics**: Dashboard panel Latency hiển thị P95 vượt ngưỡng 3000ms SLO.
2. **Traces**: Trace waterfall trên Langfuse cho thấy span `run` kéo dài ~2.6s, trong đó sub-span `retrieve` chiếm gần như toàn bộ.
3. **Logs**: Dòng log `response_sent` với `correlation_id=req-8e063992` ghi nhận `latency_ms=2651`, khớp chính xác với dữ liệu Trace.

### Fix action

- Tắt incident sau khi thu thập evidence: `python scripts/inject_incident.py --disable` ✅
- Production: Đặt timeout cho retrieval (circuit breaker pattern), thêm caching layer cho queries thường gặp, tối ưu query/index datastore, kiểm soát retry với exponential backoff.

### Preventive measure

- Alert P95/P99 tail latency với window 5 phút.
- Tạo span riêng cho từng bước retrieval để phân tách latency.
- Load test và regression test tail latency sau mỗi deploy.
- Runbook Metrics → Traces → Logs được chuẩn hóa tại `docs/alerts.md`.

## 7. Đóng góp cá nhân

| Thành viên | Phần việc | Commit/PR | Điều đã học |
|---|---|---|---|
| Nguyễn Hải Anh (2A202601670) | Middleware/correlation | commit `a399c0b` | ContextVars với structlog để bind correlation_id xuyên suốt request lifecycle |
| Tô Ngọc Hải (2A202601686) | PII/redaction | commit `a399c0b` | Regex pattern cho 6 loại PII Việt Nam; scrub đệ quy qua dict/list/str |
| Nông Ngọc Dương (2A202601296) | Metrics/dashboard | commit `a399c0b` | Tính percentile từ log JSONL; dashboard contract validation; SLO threshold |
| Nguyễn Đức Anh (2A202601870) | SLO/alert/runbook | commit `a399c0b` | Thiết kế alert theo triệu chứng người dùng; runbook Metrics→Traces→Logs |
| Lê Thị Hải Yến (2A202601570) | QA/CP3 | commit `ee272b2` | Điều tra incident: nối Metrics→Trace→Log để xác định root cause span |

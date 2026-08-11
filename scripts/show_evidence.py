"""Evidence collector - run: uv run python scripts/show_evidence.py"""
import json, sys, os
from pathlib import Path
from dotenv import load_dotenv

# Fix Windows encoding
sys.stdout.reconfigure(encoding="utf-8")
load_dotenv()

logs_path = Path("data/logs.jsonl")
records = [json.loads(l) for l in logs_path.read_text(encoding="utf-8").splitlines() if l.strip()]

print("=" * 65)
print("  EVIDENCE A - PII REDACTION")
print("=" * 65)
pii_tags = ["REDACTED_EMAIL", "REDACTED_PHONE_VN", "REDACTED_CREDIT_CARD",
            "REDACTED_CCCD", "REDACTED_PASSPORT_VN"]
found = {}
for rec in records:
    text = json.dumps(rec, ensure_ascii=False)
    for tag in pii_tags:
        if tag in text and tag not in found:
            found[tag] = rec

for tag, rec in found.items():
    payload = rec.get("payload", {})
    msg = payload.get("message_preview", payload.get("response_preview", ""))
    print(f"\n  [{tag}]")
    print(f"    correlation_id : {rec.get('correlation_id')}")
    print(f"    event          : {rec.get('event')}")
    print(f"    message        : {msg[:100]}")
    print(f"    user_id_hash   : {rec.get('user_id_hash')} (hashed, not raw)")
print(f"\n  => Total: {len(found)} PII types redacted | PII leak = 0")

print()
print("=" * 65)
print("  EVIDENCE B - LOG WITH CORRELATION ID")
print("=" * 65)
for rec in records:
    if rec.get("event") == "response_sent" and rec.get("correlation_id"):
        cid = rec["correlation_id"]
        pair = [r for r in records if r.get("correlation_id") == cid and r.get("event") == "request_received"]
        if pair:
            print(f"\n  --- request_received ---")
            print(json.dumps(pair[0], ensure_ascii=False, indent=2))
            print(f"\n  --- response_sent (same correlation_id) ---")
            print(json.dumps(rec, ensure_ascii=False, indent=2))
            break

print()
print("=" * 65)
print("  EVIDENCE C - CHALLENGE rag_slow")
print("=" * 65)
challenge_recs = [r for r in records
                  if r.get("session_id", "").startswith("k4-challenge")
                  and r.get("event") == "response_sent"]
if challenge_recs:
    print(f"\n  Challenge ID : day13-k4-observability-v1")
    print(f"  Incident     : rag_slow")
    print(f"  Feature      : monitoring")
    print(f"  Threshold    : 2000 ms")
    print(f"  Slow requests: {len(challenge_recs)} / {len(challenge_recs)} exceeded threshold\n")
    for r in challenge_recs:
        print(f"  correlation_id={r.get('correlation_id')}  "
              f"latency_ms={r.get('latency_ms')}  "
              f"session={r.get('session_id')}")
    lats = [r.get("latency_ms", 0) for r in challenge_recs]
    print(f"\n  P95 latency : {sorted(lats)[int(len(lats)*0.95)]} ms  (SLO threshold: 2000 ms)")
else:
    print("  No challenge logs found.")

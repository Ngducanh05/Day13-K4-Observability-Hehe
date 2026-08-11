from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from app.challenge import load_challenge
from app.pii import scrub_text


def load_logs(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        raise FileNotFoundError(f"Không tìm thấy {path}. Hãy chạy API/load test trước.")
    records: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            item = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(item, dict):
            records.append(item)
    return records


def find_pii_leaks(path: Path) -> list[int]:
    leaks: list[int] = []
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if line and scrub_text(line) != line:
            leaks.append(number)
    return leaks


def main() -> int:
    parser = argparse.ArgumentParser(description="QA + CP3 evidence helper")
    parser.add_argument("--logs", type=Path, default=Path("data/logs.jsonl"))
    parser.add_argument("--challenge", type=Path, default=Path("config/challenge.json"))
    args = parser.parse_args()

    challenge = load_challenge(args.challenge)
    records = load_logs(args.logs)
    relevant = [
        record for record in records
        if record.get("feature") == challenge.affected_feature
        and record.get("event") in {"response_sent", "request_failed"}
    ]
    slow = [
        record for record in relevant
        if isinstance(record.get("latency_ms"), (int, float))
        and float(record["latency_ms"]) >= challenge.latency_threshold_ms
    ]

    print("=== CP3 Challenge Evidence Helper ===")
    print(f"Challenge ID: {challenge.challenge_id}")
    print(f"Incident from released config: {challenge.incident}")
    print(f"Affected feature: {challenge.affected_feature}")
    print(f"Latency threshold: {challenge.latency_threshold_ms} ms")
    print(f"Relevant response/error logs: {len(relevant)}")
    print(f"Slow responses >= threshold: {len(slow)}")

    for record in sorted(slow, key=lambda item: float(item.get("latency_ms") or 0), reverse=True)[:5]:
        print(
            "- correlation_id={cid} latency_ms={latency} session_id={session}".format(
                cid=record.get("correlation_id", "<missing>"),
                latency=record.get("latency_ms", "<missing>"),
                session=record.get("session_id", "<missing>"),
            )
        )

    leaks = find_pii_leaks(args.logs)
    print(f"Potential PII leak lines: {len(leaks)}")
    if leaks:
        print("Leak line numbers:", ", ".join(map(str, leaks[:20])))

    print("\nNEXT:")
    print("1. Mở Langfuse và chọn một trace chậm của feature ở trên.")
    print("2. Ghi trace ID + span retrieval chậm vào submission/REPORT.md.")
    print("3. Tìm log bằng correlation ID tương ứng và lưu ảnh evidence.")
    print("4. Chỉ kết luận root cause khi Metrics → Trace → Log cùng khớp.")
    return 0 if slow and not leaks else 1


if __name__ == "__main__":
    raise SystemExit(main())

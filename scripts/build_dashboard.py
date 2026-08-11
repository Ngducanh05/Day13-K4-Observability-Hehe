from __future__ import annotations

import argparse
import html
import json
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path
from statistics import mean
from typing import Any

import yaml


def _parse_ts(value: Any) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _percentile(values: list[float], p: int) -> float:
    if not values:
        return 0.0
    items = sorted(values)
    idx = max(0, min(len(items) - 1, round((p / 100) * len(items) + 0.5) - 1))
    return float(items[idx])


def load_records(path: Path, minutes: int) -> list[dict[str, Any]]:
    if not path.exists():
        raise FileNotFoundError(f"Không tìm thấy log: {path}")

    parsed: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(record, dict):
            parsed.append(record)

    cutoff = datetime.now(timezone.utc) - timedelta(minutes=minutes)
    return [
        record
        for record in parsed
        if (ts := _parse_ts(record.get("ts"))) is not None and ts >= cutoff
    ]


def load_contract(path: Path) -> dict[str, Any]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    return payload["dashboard"]


def calculate(records: list[dict[str, Any]], minutes: int) -> dict[str, Any]:
    responses = [r for r in records if r.get("event") == "response_sent"]
    requests = [r for r in records if r.get("event") == "request_received"]
    failures = [r for r in records if r.get("event") == "request_failed"]

    latencies = [float(r["latency_ms"]) for r in responses if isinstance(r.get("latency_ms"), (int, float))]
    costs = [float(r["cost_usd"]) for r in responses if isinstance(r.get("cost_usd"), (int, float))]
    qualities = [float(r["quality_score"]) for r in responses if isinstance(r.get("quality_score"), (int, float))]
    tokens_in = sum(int(r.get("tokens_in") or 0) for r in responses)
    tokens_out = sum(int(r.get("tokens_out") or 0) for r in responses)
    error_breakdown = Counter(str(r.get("error_type") or "unknown") for r in failures)

    return {
        "latency": {"p50": _percentile(latencies, 50), "p95": _percentile(latencies, 95), "p99": _percentile(latencies, 99)},
        "traffic": {"count": len(requests), "rate_per_minute": len(requests) / max(minutes, 1)},
        "errors": {"error_rate_pct": (len(failures) / len(requests) * 100) if requests else 0.0, "breakdown": dict(error_breakdown)},
        "cost": {"total": sum(costs)},
        "tokens": {"tokens_in": tokens_in, "tokens_out": tokens_out},
        "quality": {"mean": mean(qualities) if qualities else 0.0},
    }


def _status(value: float, operator: str, threshold: float) -> str:
    passed = value <= threshold if operator == "lte" else value >= threshold
    return "OK" if passed else "BREACH"


def render_html(contract: dict[str, Any], values: dict[str, Any]) -> str:
    panel_by_id = {panel["id"]: panel for panel in contract["panels"]}
    cards = []

    latency = values["latency"]
    p = panel_by_id["latency"]
    cards.append((p["title"], f"P50 {latency['p50']:.0f} · P95 {latency['p95']:.0f} · P99 {latency['p99']:.0f} ms", latency["p95"], p))

    traffic = values["traffic"]
    p = panel_by_id["traffic"]
    cards.append((p["title"], f"{traffic['count']} requests · {traffic['rate_per_minute']:.2f} req/min", traffic["rate_per_minute"], p))

    errors = values["errors"]
    p = panel_by_id["errors"]
    breakdown = ", ".join(f"{k}: {v}" for k, v in errors["breakdown"].items()) or "none"
    cards.append((p["title"], f"{errors['error_rate_pct']:.2f}% · {html.escape(breakdown)}", errors["error_rate_pct"], p))

    cost = values["cost"]
    p = panel_by_id["cost"]
    cards.append((p["title"], f"${cost['total']:.6f} total", cost["total"], p))

    tokens = values["tokens"]
    p = panel_by_id["tokens"]
    cards.append((p["title"], f"{tokens['tokens_in']} input · {tokens['tokens_out']} output", float(tokens["tokens_in"] + tokens["tokens_out"]), p))

    quality = values["quality"]
    p = panel_by_id["quality"]
    cards.append((p["title"], f"{quality['mean']:.3f}", quality["mean"], p))

    rendered_cards = []
    for title, display, threshold_value, panel in cards:
        threshold = panel["threshold"]
        state = _status(float(threshold_value), str(threshold["operator"]), float(threshold["value"]))
        rendered_cards.append(f"""
        <section class="card">
          <div class="eyebrow">{html.escape(panel['id'].upper())}</div>
          <h2>{html.escape(title)}</h2>
          <div class="value">{display}</div>
          <div class="meta">Unit: {html.escape(str(panel['unit']))}</div>
          <div class="threshold {state.lower()}">{state} · {html.escape(str(threshold['aggregation']))} {html.escape(str(threshold['operator']))} {threshold['value']}</div>
        </section>""")

    return f"""<!doctype html>
<html><head><meta charset="utf-8"><meta http-equiv="refresh" content="{contract['refresh_seconds']}">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>{html.escape(contract['title'])}</title>
<style>
:root{{color-scheme:dark;font-family:Inter,ui-sans-serif,system-ui,sans-serif}}body{{margin:0;background:#0b1020;color:#eef2ff}}
main{{max-width:1180px;margin:0 auto;padding:36px 24px 56px}}header{{display:flex;justify-content:space-between;gap:24px;align-items:end;margin-bottom:24px}}
h1{{margin:0;font-size:32px;letter-spacing:-.03em}}.sub{{color:#a5b4fc;font-size:14px}}.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:16px}}
.card{{background:#11182d;border:1px solid #263453;border-radius:18px;padding:22px;min-height:170px}}.eyebrow{{color:#93c5fd;font-size:12px;letter-spacing:.12em;font-weight:700}}
h2{{margin:8px 0 22px;font-size:17px}}.value{{font-size:27px;font-weight:750}}.meta{{margin-top:12px;color:#94a3b8;font-size:13px}}
.threshold{{display:inline-block;margin-top:15px;padding:6px 10px;border-radius:999px;font-size:12px;font-weight:700}}.threshold.ok{{background:#123d32;color:#86efac}}.threshold.breach{{background:#4a1d2a;color:#fda4af}}
</style></head><body><main><header><div><div class="sub">Contract-backed · source data/logs.jsonl</div><h1>{html.escape(contract['title'])}</h1></div>
<div class="sub">Time range: last {contract['time_range_minutes']} min · refresh {contract['refresh_seconds']}s</div></header>
<div class="grid">{''.join(rendered_cards)}</div></main></body></html>"""


def main() -> int:
    parser = argparse.ArgumentParser(description="Build the 6-panel Day 13 dashboard")
    parser.add_argument("--logs", type=Path, default=Path("data/logs.jsonl"))
    parser.add_argument("--config", type=Path, default=Path("config/dashboard.yaml"))
    parser.add_argument("--output", type=Path, default=Path("submission/evidence/dashboard.html"))
    args = parser.parse_args()

    contract = load_contract(args.config)
    records = load_records(args.logs, int(contract["time_range_minutes"]))
    values = calculate(records, int(contract["time_range_minutes"]))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(render_html(contract, values), encoding="utf-8")
    print(f"Dashboard written: {args.output}")
    print(f"Records in {contract['time_range_minutes']}m window: {len(records)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

from datetime import datetime, timezone

from app.db import db

_sla_cache: dict[tuple[str, str], int] = {}


def _load_cache() -> None:
    rows = db().table("sla_config").select("*").execute().data or []
    _sla_cache.clear()
    for r in rows:
        _sla_cache[(r["lens_type"], r["stage"])] = r["sla_hours"]


def stage_sla_hours(lens_type: str, stage: str) -> int:
    if not _sla_cache:
        _load_cache()
    return _sla_cache.get((lens_type, stage), 24)


def _parse_ts(ts: str) -> datetime:
    return datetime.fromisoformat(ts.replace("Z", "+00:00"))


def hours_in_stage(order: dict) -> float:
    started = order.get("stage_started_at") or order["created_at"]
    return (datetime.now(timezone.utc) - _parse_ts(started)).total_seconds() / 3600.0


def sla_status(order: dict) -> dict:
    elapsed = hours_in_stage(order)
    budget = stage_sla_hours(order.get("lens_type", "Single Vision"), order.get("status", "Placed"))
    pct = (elapsed / budget * 100) if budget > 0 else 0
    remaining = budget - elapsed
    if pct >= 100:
        bucket = "breached"
    elif pct >= 80:
        bucket = "at_risk"
    else:
        bucket = "ok"
    return {
        "elapsed_hours": round(elapsed, 1),
        "sla_hours": budget,
        "remaining_hours": round(remaining, 1),
        "pct": round(pct),
        "bucket": bucket,
    }

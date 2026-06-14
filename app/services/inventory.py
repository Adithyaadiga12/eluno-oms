from app.db import db

POWER_TOLERANCE = 0.25


def _available(row: dict) -> int:
    return int(row.get("quantity", 0)) - int(row.get("reserved", 0) or 0)


def check_availability(
    lens_type: str,
    lens_index: float,
    sph: float,
    cyl: float = 0.0,
    coating: str | None = None,
) -> dict:
    """Return one of: in_stock | tolerance_match | cut_from_blank | source_from_vendor."""
    client = db()

    # 1) exact match
    q = (
        client.table("lens_inventory")
        .select("*")
        .eq("lens_type", lens_type)
        .eq("lens_index", lens_index)
        .eq("sph_power", sph)
    )
    if coating:
        q = q.eq("coating", coating)
    rows = [r for r in (q.execute().data or []) if _available(r) > 0]
    if rows:
        best = rows[0]
        return {
            "outcome": "in_stock",
            "label": "In stock",
            "message": f"In stock — {_available(best)} units of SPH {sph:+.2f} D, index {lens_index}.",
            "matched_item": best,
            "extra_hours": 0,
        }

    # 2) tolerance match (±0.25 D)
    nearby = (
        client.table("lens_inventory")
        .select("*")
        .eq("lens_type", lens_type)
        .eq("lens_index", lens_index)
        .gte("sph_power", sph - POWER_TOLERANCE)
        .lte("sph_power", sph + POWER_TOLERANCE)
        .execute()
        .data
        or []
    )
    nearby_av = [r for r in nearby if _available(r) > 0]
    if nearby_av:
        best = min(nearby_av, key=lambda r: abs(float(r["sph_power"]) - sph))
        return {
            "outcome": "tolerance_match",
            "label": "Tolerance match",
            "message": (
                f"Closest in-stock power is {float(best['sph_power']):+.2f} D "
                f"(requested {sph:+.2f} D). Within clinical tolerance — usable as-is."
            ),
            "matched_item": best,
            "extra_hours": 2,
        }

    # 3) blank available for in-house cut
    blanks = (
        client.table("lens_inventory")
        .select("*")
        .eq("lens_type", lens_type)
        .eq("lens_index", lens_index)
        .is_("coating", "null")
        .execute()
        .data
        or []
    )
    blanks_av = [r for r in blanks if _available(r) > 0]
    if blanks_av:
        return {
            "outcome": "cut_from_blank",
            "label": "Cut from blank",
            "message": "Not stocked as a finished lens, but a blank of matching index is available — cut in-house (~6 h).",
            "matched_item": blanks_av[0],
            "extra_hours": 6,
        }

    # 4) source from vendor
    return {
        "outcome": "source_from_vendor",
        "label": "Source from vendor",
        "message": "Not in stock and no compatible blank. Must source from vendor — adds 3–5 days.",
        "matched_item": None,
        "extra_hours": 72,
    }

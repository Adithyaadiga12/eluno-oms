from datetime import datetime, timezone

from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates

from app.db import db
from app.services import ai as ai_svc
from app.services import inventory as inv_svc
from app.services.alerts import fire_breach_alert
from app.services.sla import sla_status, stage_sla_hours
from app.state import can_transition, allowed_next

router = APIRouter(prefix="/api")
templates = Jinja2Templates(directory="app/templates")


@router.post("/orders/parse-rx")
async def parse_rx(request: Request, rx_photo: UploadFile = File(...)):
    img_bytes = await rx_photo.read()
    mime = rx_photo.content_type or "image/jpeg"
    parsed = ai_svc.parse_prescription_from_image(img_bytes, mime)
    return templates.TemplateResponse(
        "orders/_rx_parsed.html",
        {"request": request, "p": parsed},
    )


@router.post("/orders/check-inventory")
async def check_inventory(
    request: Request,
    lens_type: str = Form(...),
    lens_index: float = Form(...),
    sph_right: float = Form(0),
    cyl_right: float = Form(0),
    coating: str = Form(""),
):
    result = inv_svc.check_availability(
        lens_type=lens_type,
        lens_index=lens_index,
        sph=sph_right,
        cyl=cyl_right,
        coating=coating or None,
    )
    return templates.TemplateResponse(
        "orders/_inventory_result.html",
        {"request": request, "r": result},
    )


@router.post("/orders/{order_id}/status")
async def update_status(
    request: Request,
    order_id: str,
    new_status: str = Form(...),
    reason: str = Form(""),
):
    client = db()
    order = client.table("orders").select("*").eq("id", order_id).single().execute().data
    if not order:
        raise HTTPException(404, "Order not found")
    if not can_transition(order["status"], new_status):
        raise HTTPException(
            400,
            f"Invalid transition: {order['status']} -> {new_status}. "
            f"Allowed: {allowed_next(order['status'])}",
        )
    now = datetime.now(timezone.utc).isoformat()
    updates = {
        "status": new_status,
        "stage_started_at": now,
        "updated_at": now,
    }
    if new_status == "QC Failed":
        updates["reorder_count"] = (order.get("reorder_count") or 0) + 1
    client.table("orders").update(updates).eq("id", order_id).execute()
    client.table("order_status_history").insert(
        {
            "order_id": order_id,
            "from_status": order["status"],
            "to_status": new_status,
            "reason": reason or None,
            "changed_by": "ops",
        }
    ).execute()
    return JSONResponse({"ok": True, "redirect": f"/orders/{order_id}"})


@router.post("/tat/scan")
async def tat_scan(request: Request):
    client = db()
    # Pull active orders
    from app.state import ACTIVE_STATUSES

    active = (
        client.table("orders").select("*").in_("status", ACTIVE_STATUSES).execute().data or []
    )
    # Build a simple queue map: how many orders ahead at the same stage
    stage_counts: dict[str, int] = {}
    for o in active:
        stage_counts[o["status"]] = stage_counts.get(o["status"], 0) + 1

    # Score every order, alert if risk > threshold
    THRESHOLD = 0.7
    results = []
    alerts_sent = 0
    for o in active:
        sla = sla_status(o)
        # Cheap proxies for the LLM context
        hist_avg = stage_sla_hours(o["lens_type"], o["status"]) * 0.8
        ahead = max(0, stage_counts.get(o["status"], 1) - 1)
        assessment = ai_svc.predict_breach_risk(o, sla, hist_avg, ahead)
        risk = float(assessment.get("breach_risk") or 0)

        alert_result = None
        if risk >= THRESHOLD:
            # Idempotency: skip if alerted within last hour
            last = o.get("last_alert_sent_at")
            should_send = True
            if last:
                last_dt = datetime.fromisoformat(last.replace("Z", "+00:00"))
                if (datetime.now(timezone.utc) - last_dt).total_seconds() < 3600:
                    should_send = False
            if should_send:
                alert_result = fire_breach_alert(o, sla, assessment)
                client.table("orders").update(
                    {
                        "last_alert_sent_at": datetime.now(timezone.utc).isoformat(),
                        "breach_risk": risk,
                        "breach_reason": assessment.get("reason"),
                    }
                ).eq("id", o["id"]).execute()
                alerts_sent += 1

        results.append(
            {
                "order": o,
                "sla": sla,
                "assessment": assessment,
                "alert": alert_result,
            }
        )

    results.sort(key=lambda r: r["assessment"].get("breach_risk", 0), reverse=True)
    return templates.TemplateResponse(
        "tat/_scan_results.html",
        {"request": request, "results": results, "alerts_sent": alerts_sent},
    )

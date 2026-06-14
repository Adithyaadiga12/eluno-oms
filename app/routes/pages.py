from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, Form, Request, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from app.db import db
from app.services import ai as ai_svc
from app.services import inventory as inv_svc
from app.services.sla import sla_status
from app.state import ACTIVE_STATUSES, ALL_STATUSES, allowed_next, can_transition

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


def _kpis() -> dict:
    client = db()
    today_iso = datetime.now(timezone.utc).date().isoformat()
    active = (
        client.table("orders")
        .select("id", count="exact")
        .in_("status", ACTIVE_STATUSES)
        .execute()
    )
    delivered_today = (
        client.table("orders")
        .select("id", count="exact")
        .eq("status", "Delivered")
        .gte("updated_at", today_iso)
        .execute()
    )
    # at_risk and breached require SLA compute — load active rows
    active_rows = (
        client.table("orders").select("*").in_("status", ACTIVE_STATUSES).execute().data or []
    )
    at_risk = sum(1 for o in active_rows if sla_status(o)["bucket"] == "at_risk")
    breached = sum(1 for o in active_rows if sla_status(o)["bucket"] == "breached")
    return {
        "active": active.count or 0,
        "at_risk": at_risk,
        "breached": breached,
        "delivered_today": delivered_today.count or 0,
    }


@router.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    try:
        kpis = _kpis()
    except Exception as e:
        kpis = {"active": 0, "at_risk": 0, "breached": 0, "delivered_today": 0, "error": str(e)}
    return templates.TemplateResponse("index.html", {"request": request, "kpis": kpis})


@router.get("/orders", response_class=HTMLResponse)
async def orders_list(
    request: Request,
    status: str | None = None,
    lens_type: str | None = None,
    store_id: str | None = None,
):
    client = db()
    q = client.table("orders").select("*, stores(name, city)").order("created_at", desc=True)
    if status:
        q = q.eq("status", status)
    if lens_type:
        q = q.eq("lens_type", lens_type)
    if store_id:
        q = q.eq("store_id", store_id)
    rows = q.execute().data or []
    for o in rows:
        o["sla"] = sla_status(o)
    stores = client.table("stores").select("*").execute().data or []
    return templates.TemplateResponse(
        "orders/list.html",
        {
            "request": request,
            "orders": rows,
            "stores": stores,
            "statuses": ALL_STATUSES,
            "lens_types": ["Single Vision", "Bifocal", "Progressive"],
            "filter_status": status,
            "filter_lens": lens_type,
            "filter_store": store_id,
        },
    )


@router.get("/orders/new", response_class=HTMLResponse)
async def orders_new(request: Request):
    stores = db().table("stores").select("*").execute().data or []
    return templates.TemplateResponse(
        "orders/new.html",
        {"request": request, "stores": stores},
    )


@router.post("/orders", response_class=HTMLResponse)
async def orders_create(
    request: Request,
    customer_name: str = Form(...),
    customer_phone: str = Form(""),
    customer_email: str = Form(""),
    source: str = Form("Website"),
    store_id: str = Form(...),
    lens_type: str = Form(...),
    lens_index: float = Form(...),
    coating: str = Form(""),
    frame_model: str = Form(""),
    sph_right: float = Form(0),
    cyl_right: float = Form(0),
    axis_right: int = Form(0),
    add_right: float = Form(0),
    sph_left: float = Form(0),
    cyl_left: float = Form(0),
    axis_left: int = Form(0),
    add_left: float = Form(0),
    pd: float = Form(0),
):
    inv = inv_svc.check_availability(
        lens_type=lens_type,
        lens_index=lens_index,
        sph=sph_right,
        cyl=cyl_right,
        coating=coating or None,
    )
    order_number = f"ELN-{datetime.now().strftime('%Y%m%d')}-{str(uuid4())[:6].upper()}"
    new_id = str(uuid4())
    db().table("orders").insert(
        {
            "id": new_id,
            "order_number": order_number,
            "customer_name": customer_name,
            "customer_phone": customer_phone or None,
            "customer_email": customer_email or None,
            "source": source,
            "store_id": store_id,
            "lens_type": lens_type,
            "lens_index": lens_index,
            "coating": coating or None,
            "frame_model": frame_model or None,
            "sph_right": sph_right,
            "cyl_right": cyl_right,
            "axis_right": axis_right,
            "add_right": add_right,
            "sph_left": sph_left,
            "cyl_left": cyl_left,
            "axis_left": axis_left,
            "add_left": add_left,
            "pd": pd or None,
            "status": "Placed",
            "inventory_status": inv["label"],
        }
    ).execute()
    db().table("order_status_history").insert(
        {
            "order_id": new_id,
            "from_status": None,
            "to_status": "Placed",
            "reason": f"Order created. Inventory: {inv['label']}.",
            "changed_by": "system",
        }
    ).execute()
    return RedirectResponse(f"/orders/{new_id}", status_code=303)


@router.get("/orders/{order_id}", response_class=HTMLResponse)
async def order_detail(request: Request, order_id: str):
    client = db()
    order = (
        client.table("orders")
        .select("*, stores(name, city)")
        .eq("id", order_id)
        .single()
        .execute()
        .data
    )
    if not order:
        return HTMLResponse("Order not found", status_code=404)
    history = (
        client.table("order_status_history")
        .select("*")
        .eq("order_id", order_id)
        .order("created_at")
        .execute()
        .data
        or []
    )
    sla = sla_status(order)
    return templates.TemplateResponse(
        "orders/detail.html",
        {
            "request": request,
            "order": order,
            "history": history,
            "sla": sla,
            "next_statuses": allowed_next(order["status"]),
        },
    )


@router.get("/inventory", response_class=HTMLResponse)
async def inventory_page(request: Request):
    rows = (
        db()
        .table("lens_inventory")
        .select("*, stores(name)")
        .order("lens_type")
        .order("lens_index")
        .order("sph_power")
        .execute()
        .data
        or []
    )
    return templates.TemplateResponse(
        "inventory/list.html",
        {"request": request, "items": rows},
    )


@router.get("/tat-scan", response_class=HTMLResponse)
async def tat_scan_page(request: Request):
    return templates.TemplateResponse("tat/scan.html", {"request": request})

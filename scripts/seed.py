r"""
Populate Supabase with realistic eyewear OMS seed data.

Run after schema.sql has been applied:
    .\.venv\Scripts\python.exe scripts\seed.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import random
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from dotenv import load_dotenv

load_dotenv()

from app.db import db  # noqa: E402
from app.state import ACTIVE_STATUSES, OrderStatus  # noqa: E402

random.seed(42)
client = db()


# ----------------------------------------------------------------
# 1. Stores
# ----------------------------------------------------------------
STORES = [
    {"name": "Eluno Indiranagar", "city": "Bangalore"},
    {"name": "Eluno HSR Layout", "city": "Bangalore"},
    {"name": "Eluno Bandra", "city": "Mumbai"},
]
print("Seeding stores...")
client.table("stores").delete().neq("id", "00000000-0000-0000-0000-000000000000").execute()
inserted_stores = client.table("stores").insert(STORES).execute().data
store_ids = [s["id"] for s in inserted_stores]
print(f"  Inserted {len(inserted_stores)} stores.")


# ----------------------------------------------------------------
# 2. SLA Config
# Single Vision: 24h total, Bifocal: 36h, Progressive: 48h
# Stage budget distribution
# ----------------------------------------------------------------
SLA_TABLE = {
    "Single Vision": {
        "Placed": 1, "Rx Verified": 1, "Inventory Checked": 1,
        "Lens Cut": 4, "Fitting": 2, "QC": 2, "QC Failed": 1,
        "Dispatched": 4, "Delivered": 10,
    },
    "Bifocal": {
        "Placed": 1, "Rx Verified": 2, "Inventory Checked": 1,
        "Lens Cut": 6, "Fitting": 3, "QC": 3, "QC Failed": 1,
        "Dispatched": 6, "Delivered": 14,
    },
    "Progressive": {
        "Placed": 1, "Rx Verified": 2, "Inventory Checked": 2,
        "Lens Cut": 10, "Fitting": 4, "QC": 4, "QC Failed": 1,
        "Dispatched": 8, "Delivered": 16,
    },
}
print("Seeding SLA config...")
client.table("sla_config").delete().neq("id", "00000000-0000-0000-0000-000000000000").execute()
sla_rows = [
    {"lens_type": lt, "stage": st, "sla_hours": h}
    for lt, stages in SLA_TABLE.items()
    for st, h in stages.items()
]
client.table("sla_config").insert(sla_rows).execute()
print(f"  Inserted {len(sla_rows)} SLA rows.")


# ----------------------------------------------------------------
# 3. Lens Inventory
# Real eyewear: standard indices 1.50, 1.56, 1.60 widely stocked.
# 1.67 and 1.74 are sparse (only high-power needs them).
# ----------------------------------------------------------------
print("Seeding lens inventory...")
client.table("lens_inventory").delete().neq("id", "00000000-0000-0000-0000-000000000000").execute()

POWERS_COMMON = [round(p * 0.25, 2) for p in range(-16, 17)]  # -4.00 to +4.00 in 0.25 steps
POWERS_HIGH = [round(p * 0.25, 2) for p in range(-24, -16)] + [round(p * 0.25, 2) for p in range(17, 25)]
COATINGS = [None, "AR", "Blue Cut", "Photochromic"]

inv_rows = []
for store_id in store_ids:
    # 1.50 / 1.56 / 1.60 — wide coverage on common powers + a few high
    for idx in [1.50, 1.56, 1.60]:
        for sph in POWERS_COMMON:
            for coating in random.sample(COATINGS, k=random.choice([1, 2, 3])):
                inv_rows.append({
                    "lens_type": "Single Vision",
                    "lens_index": idx,
                    "sph_power": sph,
                    "cyl_power": 0,
                    "coating": coating,
                    "quantity": random.randint(0, 15),
                    "store_id": store_id,
                })
    # 1.67 / 1.74 — only high powers, sparse
    for idx in [1.67, 1.74]:
        for sph in POWERS_HIGH:
            inv_rows.append({
                "lens_type": "Single Vision",
                "lens_index": idx,
                "sph_power": sph,
                "cyl_power": 0,
                "coating": random.choice([None, "AR"]),
                "quantity": random.randint(0, 4),
                "store_id": store_id,
            })
    # Bifocal / Progressive — fewer SKUs, common index
    for lens_type in ["Bifocal", "Progressive"]:
        for idx in [1.50, 1.56]:
            for sph in [-2.0, -1.0, 0.0, 1.0, 2.0]:
                inv_rows.append({
                    "lens_type": lens_type,
                    "lens_index": idx,
                    "sph_power": sph,
                    "cyl_power": 0,
                    "coating": random.choice([None, "AR"]),
                    "quantity": random.randint(0, 6),
                    "store_id": store_id,
                })

# Insert in batches of 500
for i in range(0, len(inv_rows), 500):
    client.table("lens_inventory").insert(inv_rows[i:i + 500]).execute()
print(f"  Inserted {len(inv_rows)} inventory rows.")


# ----------------------------------------------------------------
# 4. Orders
# Spread across stages, some near breach so TAT scan fires alerts.
# ----------------------------------------------------------------
print("Seeding orders...")
client.table("orders").delete().neq("id", "00000000-0000-0000-0000-000000000000").execute()
client.table("order_status_history").delete().neq("id", "00000000-0000-0000-0000-000000000000").execute()

FIRST_NAMES = ["Aarav", "Ananya", "Rohan", "Diya", "Karthik", "Meera", "Vikram", "Shreya",
               "Arjun", "Priya", "Aditya", "Riya", "Kabir", "Anika", "Ishaan", "Kavya"]
LAST_NAMES = ["Sharma", "Patel", "Reddy", "Iyer", "Kumar", "Singh", "Nair", "Mehta", "Joshi"]
SOURCES = ["Website", "Retail Store", "Phone", "App"]
LENS_TYPES = ["Single Vision", "Bifocal", "Progressive"]
LENS_INDICES = [1.50, 1.56, 1.60, 1.67]
COATINGS_PROB = [None, "AR", "Blue Cut", "Photochromic"]
INVENTORY_OUTCOMES = ["In stock", "Tolerance match", "Cut from blank", "Source from vendor"]

# Mix of statuses, plus some near-breach for demo
status_distribution = (
    [OrderStatus.PLACED.value] * 4
    + [OrderStatus.RX_VERIFIED.value] * 4
    + [OrderStatus.INVENTORY_CHECKED.value] * 4
    + [OrderStatus.LENS_CUT.value] * 6
    + [OrderStatus.FITTING.value] * 4
    + [OrderStatus.QC.value] * 3
    + [OrderStatus.DISPATCHED.value] * 4
    + [OrderStatus.DELIVERED.value] * 6
)

orders_rows = []
history_rows = []
now = datetime.now(timezone.utc)
for i in range(len(status_distribution)):
    status = status_distribution[i]
    lens_type = random.choice(LENS_TYPES)
    lens_index = random.choice(LENS_INDICES)
    sph_r = round(random.uniform(-5, 4) * 4) / 4
    sph_l = round(random.uniform(-5, 4) * 4) / 4

    # Time progression: how long should the order have been in this stage?
    sla_h = SLA_TABLE[lens_type].get(status, 4)
    # Mix: most orders well within SLA, some near breach
    if i < 6:  # first 6 are near-breach demo data
        elapsed_h = sla_h * random.uniform(0.85, 1.3)
    else:
        elapsed_h = sla_h * random.uniform(0.05, 0.7)
    stage_started = now - timedelta(hours=elapsed_h)
    created = stage_started - timedelta(hours=random.uniform(2, 24))

    name = f"{random.choice(FIRST_NAMES)} {random.choice(LAST_NAMES)}"
    order_id = str(uuid4())
    order_number = f"ELN-{created.strftime('%Y%m%d')}-{str(uuid4())[:6].upper()}"

    orders_rows.append({
        "id": order_id,
        "order_number": order_number,
        "customer_name": name,
        "customer_phone": f"+9198{random.randint(10000000, 99999999)}",
        "customer_email": f"{name.lower().replace(' ', '.')}@example.com",
        "source": random.choice(SOURCES),
        "store_id": random.choice(store_ids),
        "sph_right": sph_r,
        "cyl_right": round(random.uniform(-2, 0) * 4) / 4 if random.random() > 0.4 else 0,
        "axis_right": random.choice([0, 90, 180, 45, 135]),
        "add_right": 0,
        "sph_left": sph_l,
        "cyl_left": round(random.uniform(-2, 0) * 4) / 4 if random.random() > 0.4 else 0,
        "axis_left": random.choice([0, 90, 180, 45, 135]),
        "add_left": 0,
        "pd": round(random.uniform(58, 68), 1),
        "lens_type": lens_type,
        "lens_index": lens_index,
        "coating": random.choice(COATINGS_PROB),
        "frame_model": random.choice(["Ray-Ban RB2140", "Vincent Chase 102", "John Jacobs JJ E10125",
                                       "Lenskart Air LA E50028", "Carrera 1024", "Oakley OX8032"]),
        "status": status,
        "inventory_status": random.choice(INVENTORY_OUTCOMES),
        "stage_started_at": stage_started.isoformat(),
        "reorder_count": 1 if status in ("Lens Cut", "QC") and random.random() < 0.15 else 0,
        "created_at": created.isoformat(),
        "updated_at": stage_started.isoformat(),
    })
    history_rows.append({
        "order_id": order_id,
        "from_status": None,
        "to_status": "Placed",
        "reason": "Order created (seed).",
        "changed_by": "system",
        "created_at": created.isoformat(),
    })
    if status != "Placed":
        history_rows.append({
            "order_id": order_id,
            "from_status": "Placed",
            "to_status": status,
            "reason": f"Moved to {status} (seed).",
            "changed_by": "ops",
            "created_at": stage_started.isoformat(),
        })

client.table("orders").insert(orders_rows).execute()
client.table("order_status_history").insert(history_rows).execute()
print(f"  Inserted {len(orders_rows)} orders and {len(history_rows)} history rows.")

print("\nSeed complete.")

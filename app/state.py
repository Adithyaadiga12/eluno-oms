from enum import Enum


class OrderStatus(str, Enum):
    PLACED = "Placed"
    RX_VERIFIED = "Rx Verified"
    INVENTORY_CHECKED = "Inventory Checked"
    LENS_CUT = "Lens Cut"
    FITTING = "Fitting"
    QC = "QC"
    QC_FAILED = "QC Failed"
    DISPATCHED = "Dispatched"
    DELIVERED = "Delivered"
    CANCELLED = "Cancelled"


ALL_STATUSES = [s.value for s in OrderStatus]

ACTIVE_STATUSES = [
    s.value
    for s in OrderStatus
    if s not in (OrderStatus.DELIVERED, OrderStatus.CANCELLED)
]

VALID_TRANSITIONS: dict[str, list[str]] = {
    OrderStatus.PLACED.value: [OrderStatus.RX_VERIFIED.value, OrderStatus.CANCELLED.value],
    OrderStatus.RX_VERIFIED.value: [OrderStatus.INVENTORY_CHECKED.value, OrderStatus.CANCELLED.value],
    OrderStatus.INVENTORY_CHECKED.value: [OrderStatus.LENS_CUT.value, OrderStatus.CANCELLED.value],
    OrderStatus.LENS_CUT.value: [OrderStatus.FITTING.value, OrderStatus.CANCELLED.value],
    OrderStatus.FITTING.value: [OrderStatus.QC.value, OrderStatus.CANCELLED.value],
    OrderStatus.QC.value: [OrderStatus.DISPATCHED.value, OrderStatus.QC_FAILED.value, OrderStatus.CANCELLED.value],
    # QC fail loops back to Lens Cut (re-order) — this is the eyewear-specific signal
    OrderStatus.QC_FAILED.value: [OrderStatus.LENS_CUT.value],
    OrderStatus.DISPATCHED.value: [OrderStatus.DELIVERED.value, OrderStatus.CANCELLED.value],
    OrderStatus.DELIVERED.value: [],
    OrderStatus.CANCELLED.value: [],
}


def allowed_next(current: str) -> list[str]:
    return VALID_TRANSITIONS.get(current, [])


def can_transition(from_status: str, to_status: str) -> bool:
    return to_status in allowed_next(from_status)

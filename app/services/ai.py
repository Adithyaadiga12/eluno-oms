import json

import google.generativeai as genai

from app.config import settings

genai.configure(api_key=settings.gemini_api_key)

MODEL_NAME = "gemini-2.5-flash"


def _model():
    return genai.GenerativeModel(MODEL_NAME)


PRESCRIPTION_PROMPT = """You are a medical prescription parser for an eyewear retailer.

Look at the prescription image and extract the eye prescription. Return ONLY a JSON object with this exact shape:

{
  "sph_right": number or null,
  "cyl_right": number or null,
  "axis_right": integer 0-180 or null,
  "add_right": number or null,
  "sph_left": number or null,
  "cyl_left": number or null,
  "axis_left": integer 0-180 or null,
  "add_left": number or null,
  "pd": number or null,
  "confidence": float between 0 and 1,
  "notes": "any legibility concerns, or empty string"
}

Rules:
- SPH (sphere): typically -10.00 to +10.00, in 0.25 steps
- CYL (cylinder): typically -6.00 to 0.00 (negative convention)
- AXIS: integer 0-180, only meaningful when CYL is non-zero
- ADD: positive, typically +0.75 to +3.00, used only for bifocal / progressive
- PD (pupillary distance): typically 50-75 mm
- Right eye is sometimes labelled "OD"; left eye "OS"
- Use null when a value is illegible or absent — do NOT guess
- confidence: 0.9+ if clearly legible, 0.5-0.8 if some ambiguity, below 0.5 if mostly illegible

Return ONLY the JSON object. No markdown fences, no commentary.
"""


def parse_prescription_from_image(image_bytes: bytes, mime_type: str = "image/jpeg") -> dict:
    try:
        resp = _model().generate_content(
            [PRESCRIPTION_PROMPT, {"mime_type": mime_type, "data": image_bytes}],
            generation_config={"response_mime_type": "application/json"},
        )
        return json.loads(resp.text)
    except Exception as e:
        return {
            "error": str(e),
            "confidence": 0.0,
            "notes": "AI parse failed — fill in manually",
        }


def predict_breach_risk(order: dict, sla: dict, historical_avg_hours: float, queue_ahead: int) -> dict:
    prompt = f"""You are an order operations analyst for an eyewear lab. Assess SLA breach risk for the order below and explain it like a colleague would.

Order context:
- Order #: {order.get('order_number')}
- Lens type: {order.get('lens_type')}
- Current stage: {order.get('status')}
- Time in current stage: {sla['elapsed_hours']} h
- Stage SLA: {sla['sla_hours']} h
- SLA used: {sla['pct']}%
- Inventory outcome at intake: {order.get('inventory_status', 'unknown')}
- Re-order count (QC failures): {order.get('reorder_count', 0)}
- Historical avg time for this stage on similar lens type: {historical_avg_hours} h
- Orders ahead at this stage: {queue_ahead}

Output JSON:
{{
  "breach_risk": float 0.0-1.0,
  "reason": "1-2 sentences referencing concrete numbers above",
  "suggested_action": "1 sentence — what should the team do?"
}}

Return ONLY the JSON object. No markdown fences.
"""
    try:
        resp = _model().generate_content(
            prompt,
            generation_config={"response_mime_type": "application/json"},
        )
        return json.loads(resp.text)
    except Exception as e:
        return {
            "breach_risk": 0.5,
            "reason": f"AI assessment unavailable ({e}); fall back to manual review.",
            "suggested_action": "Manual review by ops lead",
        }

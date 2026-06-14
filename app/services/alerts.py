import resend
from twilio.rest import Client as TwilioClient

from app.config import settings


def send_email_alert(subject: str, html_body: str) -> dict:
    if not settings.resend_api_key or not settings.alert_email_to:
        return {"ok": False, "channel": "email", "reason": "Resend not configured"}
    resend.api_key = settings.resend_api_key
    try:
        r = resend.Emails.send(
            {
                "from": "Eluno OMS <onboarding@resend.dev>",
                "to": [settings.alert_email_to],
                "subject": subject,
                "html": html_body,
            }
        )
        return {"ok": True, "channel": "email", "id": r.get("id")}
    except Exception as e:
        return {"ok": False, "channel": "email", "reason": str(e)}


def send_whatsapp_alert(body: str) -> dict:
    if not (settings.twilio_account_sid and settings.twilio_auth_token and settings.alert_whatsapp_to):
        return {"ok": False, "channel": "whatsapp", "reason": "Twilio not configured"}
    try:
        client = TwilioClient(settings.twilio_account_sid, settings.twilio_auth_token)
        msg = client.messages.create(
            from_=settings.twilio_whatsapp_from,
            to=settings.alert_whatsapp_to,
            body=body,
        )
        return {"ok": True, "channel": "whatsapp", "sid": msg.sid}
    except Exception as e:
        return {"ok": False, "channel": "whatsapp", "reason": str(e)}


def fire_breach_alert(order: dict, sla: dict, ai_assessment: dict) -> dict:
    subject = f"[Eluno OMS] SLA risk: {order['order_number']} ({order['lens_type']})"
    html = f"""
    <h2>SLA breach risk on order {order['order_number']}</h2>
    <p><strong>Customer:</strong> {order.get('customer_name','')}</p>
    <p><strong>Lens type:</strong> {order.get('lens_type')}</p>
    <p><strong>Current stage:</strong> {order.get('status')} — {sla['elapsed_hours']} h of {sla['sla_hours']} h ({sla['pct']}%)</p>
    <p><strong>Risk score:</strong> {round(ai_assessment.get('breach_risk', 0) * 100)}%</p>
    <p><strong>Why:</strong> {ai_assessment.get('reason','')}</p>
    <p><strong>Suggested action:</strong> {ai_assessment.get('suggested_action','')}</p>
    """
    sms = (
        f"Eluno OMS alert\n"
        f"Order {order['order_number']} ({order['lens_type']})\n"
        f"Stage {order['status']} — {sla['pct']}% of SLA used\n"
        f"Risk {round(ai_assessment.get('breach_risk', 0) * 100)}%\n"
        f"{ai_assessment.get('reason','')}"
    )
    return {
        "email": send_email_alert(subject, html),
        "whatsapp": send_whatsapp_alert(sms),
    }

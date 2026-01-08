from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, EmailStr
from typing import List, Optional
import os
import requests

app = FastAPI(
    title="Pedidos Mailer",
    version="1.0.0"
)

# =========================
# MODELOS
# =========================

class OrderItem(BaseModel):
    producto: str
    cantidad: int
    precio_unitario: Optional[float] = None


class OrderPayload(BaseModel):
    order_id: str
    cliente_nombre: str
    cliente_email: Optional[EmailStr] = None
    cliente_telefono: Optional[str] = None
    notas: Optional[str] = None
    items: List[OrderItem]
    total: Optional[float] = None


# =========================
# EMAIL (SENDGRID API)
# =========================

def send_email(subject: str, html_body: str, to_email: str) -> None:
    api_key = os.getenv("SENDGRID_API_KEY")
    from_email = os.getenv("MAIL_FROM")
    from_name = os.getenv("MAIL_FROM_NAME", "Pedidos")

    if not api_key:
        raise RuntimeError("Falta SENDGRID_API_KEY")
    if not from_email:
        raise RuntimeError("Falta MAIL_FROM")

    url = "https://api.sendgrid.com/v3/mail/send"

    payload = {
        "personalizations": [
            {
                "to": [{"email": to_email}]
            }
        ],
        "from": {
            "email": from_email,
            "name": from_name
        },
        "subject": subject,
        "content": [
            {
                "type": "text/html",
                "value": html_body
            }
        ]
    }

    response = requests.post(
        url,
        json=payload,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        },
        timeout=20
    )

    # SendGrid devuelve 202 cuando acepta el envío
    if response.status_code not in (200, 202):
        raise RuntimeError(
            f"SendGrid error {response.status_code}: {response.text}"
        )


# =========================
# HTML DEL PEDIDO
# =========================

def render_order_html(p: OrderPayload) -> str:
    rows = ""
    for item in p.items:
        pu = (
            f"${item.precio_unitario:,.2f}"
            if item.precio_unitario is not None
            else "-"
        )
        rows += f"""
        <tr>
            <td style="padding:8px;border-bottom:1px solid #ddd;">{item.producto}</td>
            <td style="padding:8px;border-bottom:1px solid #ddd;text-align:right;">{item.cantidad}</td>
            <td style="padding:8px;border-bottom:1px solid #ddd;text-align:right;">{pu}</td>
        </tr>
        """

    total = f"${p.total:,.2f}" if p.total is not None else "-"

    return f"""
    <div style="font-family:Arial,sans-serif;max-width:720px">
        <h2>Nuevo pedido recibido</h2>

        <p><b>ID Pedido:</b> {p.order_id}</p>
        <p><b>Cliente:</b> {p.cliente_nombre}</p>
        <p><b>Email:</b> {p.cliente_email or "-"}</p>
        <p><b>Teléfono:</b> {p.cliente_telefono or "-"}</p>
        <p><b>Notas:</b> {p.notas or "-"}</p>

        <h3>Detalle del pedido</h3>

        <table style="width:100%;border-collapse:collapse;">
            <thead>
                <tr>
                    <th style="text-align:left;padding:8px;border-bottom:2px solid #000;">Producto</th>
                    <th style="text-align:right;padding:8px;border-bottom:2px solid #000;">Cantidad</th>
                    <th style="text-align:right;padding:8px;border-bottom:2px solid #000;">Precio Unit.</th>
                </tr>
            </thead>
            <tbody>
                {rows}
            </tbody>
        </table>

        <p style="margin-top:16px;"><b>Total:</b> {total}</p>

        <hr style="margin:24px 0;">
        <p style="font-size:12px;color:#666;">
            Generado automáticamente por el Asistente de Pedidos.
        </p>
    </div>
    """


# =========================
# ENDPOINTS
# =========================

@app.get("/")
def healthcheck():
    return {"ok": True, "service": "pedidos-mailer"}


@app.post("/send-order-email")
def send_order_email(payload: OrderPayload):
    to_email = os.getenv("GMAIL_TO")
    if not to_email:
        raise HTTPException(
            status_code=500,
            detail="Falta GMAIL_TO en variables de entorno"
        )

    subject = f"Pedido {payload.order_id} - {payload.cliente_nombre}"
    html = render_order_html(payload)

    try:
        send_email(subject, html, to_email)
        return {"ok": True, "sent_to": to_email}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

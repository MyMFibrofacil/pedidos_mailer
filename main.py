from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, EmailStr
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

app = FastAPI(title="Pedidos Mailer", version="1.0.0")

class OrderItem(BaseModel):
    producto: str
    cantidad: int
    precio_unitario: float | None = None

class OrderPayload(BaseModel):
    order_id: str
    cliente_nombre: str
    cliente_email: EmailStr | None = None
    cliente_telefono: str | None = None
    notas: str | None = None
    items: list[OrderItem]
    total: float | None = None

def send_email(subject: str, html_body: str, to_email: str) -> None:
    gmail_user = os.getenv("GMAIL_USER")
    gmail_app_password = os.getenv("GMAIL_APP_PASSWORD")
    mail_from_name = os.getenv("MAIL_FROM_NAME", "Asistente de Pedidos")
    smtp_host = os.getenv("SMTP_HOST", "smtp.gmail.com")
    smtp_port = int(os.getenv("SMTP_PORT", "465"))

    if not gmail_user or not gmail_app_password:
        raise RuntimeError("Faltan GMAIL_USER o GMAIL_APP_PASSWORD en variables de entorno.")

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = f"{mail_from_name} <{gmail_user}>"
    msg["To"] = to_email

    msg.attach(MIMEText(html_body, "html", "utf-8"))

    with smtplib.SMTP_SSL(smtp_host, smtp_port, timeout=20) as server:
        server.login(gmail_user, gmail_app_password)
        server.sendmail(gmail_user, [to_email], msg.as_string())

def render_order_html(p: OrderPayload) -> str:
    rows = ""
    for it in p.items:
        pu = f"${it.precio_unitario:,.2f}" if it.precio_unitario is not None else "-"
        rows += f"""
        <tr>
          <td style="padding:8px;border-bottom:1px solid #eee;">{it.producto}</td>
          <td style="padding:8px;border-bottom:1px solid #eee;text-align:right;">{it.cantidad}</td>
          <td style="padding:8px;border-bottom:1px solid #eee;text-align:right;">{pu}</td>
        </tr>
        """

    total = f"${p.total:,.2f}" if p.total is not None else "-"

    return f"""
    <div style="font-family:Arial,sans-serif;max-width:720px">
      <h2>Nuevo pedido recibido: {p.order_id}</h2>
      <p><b>Cliente:</b> {p.cliente_nombre}</p>
      <p><b>Email:</b> {p.cliente_email or "-"}</p>
      <p><b>Teléfono:</b> {p.cliente_telefono or "-"}</p>
      <p><b>Notas:</b> {p.notas or "-"}</p>

      <h3>Items</h3>
      <table style="width:100%;border-collapse:collapse;">
        <thead>
          <tr>
            <th style="text-align:left;padding:8px;border-bottom:2px solid #ddd;">Producto</th>
            <th style="text-align:right;padding:8px;border-bottom:2px solid #ddd;">Cantidad</th>
            <th style="text-align:right;padding:8px;border-bottom:2px solid #ddd;">Precio Unit.</th>
          </tr>
        </thead>
        <tbody>
          {rows}
        </tbody>
      </table>

      <p style="margin-top:16px;"><b>Total:</b> {total}</p>
      <hr style="border:none;border-top:1px solid #eee;margin:24px 0;">
      <p style="color:#666;font-size:12px;">Generado automáticamente por el Asistente de Pedidos.</p>
    </div>
    """

@app.post("/send-order-email")
def send_order_email(payload: OrderPayload):
    to_email = os.getenv("GMAIL_TO")  # tu casilla destino
    if not to_email:
        raise HTTPException(status_code=500, detail="Falta GMAIL_TO en variables de entorno.")

    subject = f"Pedido {payload.order_id} - {payload.cliente_nombre}"
    html = render_order_html(payload)

    try:
        send_email(subject, html, to_email)
        return {"ok": True, "sent_to": to_email}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

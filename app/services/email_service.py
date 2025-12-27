from typing import Optional, List
from email.message import EmailMessage
import aiosmtplib
import os
import html

def build_order_success_html(customer_name: str, order_id: str, total_amount: float, items: List[dict]) -> str:
    support_email = os.getenv("SUPPORT_EMAIL", "support@snuggle.com")

    safe_customer = html.escape(customer_name)
    safe_order = html.escape(order_id)

    items_html = ""
    for it in items:
        name = html.escape(str(it.get("name", "Item")))
        qty = int(it.get("qty", 1))
        price = float(it.get("price", 0))

        items_html += f"""
        <tr>
          <td style="padding:10px;border-bottom:1px solid #eee;">{name}</td>
          <td style="padding:10px;border-bottom:1px solid #eee;text-align:center;">{qty}</td>
          <td style="padding:10px;border-bottom:1px solid #eee;text-align:right;">₹{price:,.2f}</td>
        </tr>
        """

    return f"""
    <div style="font-family:Inter,Arial,sans-serif;background:#f7f7fb;padding:24px;">
      <div style="max-width:680px;margin:0 auto;background:#ffffff;border-radius:16px;overflow:hidden;box-shadow:0 6px 18px rgba(0,0,0,0.06);">
        
        <div style="background:linear-gradient(90deg,#ff6aa2,#7c3aed);padding:20px 24px;color:#fff;">
          <div style="font-size:18px;font-weight:700;">Snuggle 💜</div>
          <div style="opacity:.95;margin-top:4px;">Your order is confirmed</div>
        </div>

        <div style="padding:22px 24px;color:#111827;">
          <h2 style="margin:0 0 10px 0;font-size:22px;">Thank you, {safe_customer} ✨</h2>
          <p style="margin:0 0 14px 0;line-height:1.6;color:#374151;">
            We’re so happy you chose Snuggle. Your order has been placed successfully and we’re already preparing it with lots of care 🫶
          </p>

          <div style="background:#f3f4f6;border-radius:12px;padding:14px 16px;margin:16px 0;">
            <div style="display:flex;justify-content:space-between;gap:10px;flex-wrap:wrap;">
              <div>
                <div style="font-size:12px;color:#6b7280;">Order ID</div>
                <div style="font-weight:700;">#{safe_order}</div>
              </div>
              <div style="text-align:right;">
                <div style="font-size:12px;color:#6b7280;">Total</div>
                <div style="font-weight:800;font-size:16px;">₹{total_amount:,.2f}</div>
              </div>
            </div>
          </div>

          <h3 style="margin:18px 0 10px 0;font-size:16px;">Order Summary</h3>
          <table style="width:100%;border-collapse:collapse;border:1px solid #eee;border-radius:12px;overflow:hidden;">
            <thead>
              <tr style="background:#fafafa;">
                <th style="text-align:left;padding:10px;border-bottom:1px solid #eee;">Item</th>
                <th style="text-align:center;padding:10px;border-bottom:1px solid #eee;">Qty</th>
                <th style="text-align:right;padding:10px;border-bottom:1px solid #eee;">Price</th>
              </tr>
            </thead>
            <tbody>
              {items_html}
            </tbody>
            <tfoot>
              <tr>
                <td colspan="2" style="padding:10px;text-align:right;font-weight:700;">Total</td>
                <td style="padding:10px;text-align:right;font-weight:800;">₹{total_amount:,.2f}</td>
              </tr>
            </tfoot>
          </table>

          <p style="margin:16px 0 0 0;color:#374151;line-height:1.6;">
            Any question? Reply to this mail or contact:
            <a href="mailto:{support_email}" style="color:#7c3aed;text-decoration:none;">{support_email}</a>
          </p>

          <div style="margin-top:18px;padding:14px 16px;background:#fff7ed;border:1px solid #fed7aa;border-radius:12px;color:#9a3412;">
            <strong>Little note 💛</strong><br/>
            We don’t just pack orders — we pack happiness. Thank you for supporting our small dream.
          </div>
        </div>

        <div style="padding:16px 24px;background:#111827;color:#e5e7eb;">
          <div style="font-size:13px;opacity:.9;">With love,</div>
          <div style="font-size:15px;font-weight:700;margin-top:2px;">Team Snuggle 🧸</div>
        </div>

      </div>
    </div>
    """

class EmailService:
    def __init__(self):
        self.smtp_host = os.getenv("SMTP_HOST", "")
        self.smtp_port = int(os.getenv("SMTP_PORT", "587"))
        self.smtp_user = os.getenv("SMTP_USER", "")
        self.smtp_pass = os.getenv("SMTP_PASS", "")
        self.email_from = os.getenv("EMAIL_FROM") or f"Snuggle <{self.smtp_user}>"

    async def send_email(self, to_email: str, subject: str, html_body: str, text_body: Optional[str] = None):
        if not (self.smtp_host and self.smtp_user and self.smtp_pass):
            raise ValueError("SMTP config missing. Please set SMTP_HOST/SMTP_USER/SMTP_PASS in .env")

        msg = EmailMessage()
        msg["From"] = self.email_from
        msg["To"] = to_email
        msg["Subject"] = subject
        msg["Reply-To"] = os.getenv("SUPPORT_EMAIL", "support@snuggle.com")

        msg.set_content(text_body or "Order confirmed! (Your email client does not support HTML)")
        msg.add_alternative(html_body, subtype="html")

        await aiosmtplib.send(
            msg,
            hostname=self.smtp_host,
            port=self.smtp_port,
            start_tls=True,
            username=self.smtp_user,
            password=self.smtp_pass,
            timeout=20,
        )

    async def send_order_success_email(self, to_email: str, customer_name: str, order_id: str, total_amount: float, items: List[dict]):
        subject = f"Order Confirmed 🎉 #{order_id} | Snuggle"
        html_body = build_order_success_html(customer_name, order_id, total_amount, items)
        text_body = f"Thank you {customer_name}! Your order #{order_id} is confirmed. Total: ₹{total_amount:,.2f}"
        await self.send_email(to_email, subject, html_body, text_body=text_body)

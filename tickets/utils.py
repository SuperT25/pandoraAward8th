"""
Pandora E-Ticket System — Utility functions
QR code generation, PDF ticket generation, IP helper
"""

import io
import os
import qrcode
from django.conf import settings
from django.utils import timezone


# ---------------------------------------------------------------------------
# IP Address helper
# ---------------------------------------------------------------------------

def get_client_ip(request):
    x_forwarded = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded:
        return x_forwarded.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR')


# ---------------------------------------------------------------------------
# QR Code generation
# ---------------------------------------------------------------------------

def generate_qr_image(qr_token: str, size: int = 10) -> bytes:
    """
    Generate a QR code PNG for the given token.
    The QR contains ONLY the token — no personal data.
    Returns PNG bytes.
    """
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=size,
        border=2,
    )
    qr.add_data(qr_token)
    qr.make(fit=True)
    img = qr.make_image(fill_color="#1a0a00", back_color="white")
    buffer = io.BytesIO()
    img.save(buffer, format='PNG')
    return buffer.getvalue()


def save_qr_to_file(ticket) -> str:
    """
    Generate and save QR PNG to media/qrcodes/<ticket_number>.png
    Returns the relative media path.
    """
    png_bytes = generate_qr_image(ticket.qr_token)
    rel_path = f"qrcodes/{ticket.ticket_number}.png"
    abs_path = os.path.join(settings.MEDIA_ROOT, rel_path)
    os.makedirs(os.path.dirname(abs_path), exist_ok=True)
    with open(abs_path, 'wb') as f:
        f.write(png_bytes)
    return rel_path


# ---------------------------------------------------------------------------
# PDF Ticket generation  (ReportLab)
# ---------------------------------------------------------------------------

def generate_ticket_pdf(ticket) -> bytes:
    """
    Generate a professional Pandora-branded PDF ticket.
    Returns PDF bytes.
    """
    from reportlab.lib.pagesizes import A6, landscape
    from reportlab.lib.units import mm
    from reportlab.lib import colors
    from reportlab.lib.utils import ImageReader
    from reportlab.pdfgen import canvas
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from PIL import Image as PILImage

    # A6 landscape  148 x 105 mm
    PAGE_W, PAGE_H = landscape(A6)

    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=(PAGE_W, PAGE_H))

    # ── Background ──────────────────────────────────────────────────────────
    c.setFillColor(colors.HexColor('#0d0500'))
    c.rect(0, 0, PAGE_W, PAGE_H, fill=1, stroke=0)

    # Gold gradient stripe top
    c.setFillColor(colors.HexColor('#c9960c'))
    c.rect(0, PAGE_H - 8 * mm, PAGE_W, 8 * mm, fill=1, stroke=0)

    # Gold stripe bottom
    c.rect(0, 0, PAGE_W, 5 * mm, fill=1, stroke=0)

    # ── Left panel — guest photo ────────────────────────────────────────────
    photo_x, photo_y = 6 * mm, 14 * mm
    photo_w, photo_h = 38 * mm, 50 * mm
    c.setStrokeColor(colors.HexColor('#c9960c'))
    c.setLineWidth(1.5)
    c.rect(photo_x, photo_y, photo_w, photo_h, fill=0, stroke=1)

    if ticket.guest.photo and hasattr(ticket.guest.photo, 'path'):
        try:
            photo_path = ticket.guest.photo.path
            c.drawImage(
                ImageReader(photo_path),
                photo_x, photo_y, photo_w, photo_h,
                preserveAspectRatio=True, mask='auto',
            )
        except Exception:
            # Photo not found — draw placeholder text
            c.setFillColor(colors.HexColor('#3a2000'))
            c.rect(photo_x, photo_y, photo_w, photo_h, fill=1, stroke=0)
            c.setFillColor(colors.HexColor('#c9960c'))
            c.setFont('Helvetica', 7)
            c.drawCentredString(photo_x + photo_w / 2, photo_y + photo_h / 2, 'PHOTO')
    else:
        c.setFillColor(colors.HexColor('#3a2000'))
        c.rect(photo_x, photo_y, photo_w, photo_h, fill=1, stroke=0)
        c.setFillColor(colors.HexColor('#c9960c'))
        c.setFont('Helvetica', 7)
        c.drawCentredString(photo_x + photo_w / 2, photo_y + photo_h / 2, 'PHOTO')

    # ── Centre panel ────────────────────────────────────────────────────────
    cx = 52 * mm
    cy_top = PAGE_H - 10 * mm

    # Pandora Awards title
    c.setFillColor(colors.HexColor('#c9960c'))
    c.setFont('Helvetica-Bold', 12)
    c.drawString(cx, cy_top, 'PANDORA AWARDS')

    c.setFont('Helvetica', 7)
    c.setFillColor(colors.HexColor('#e8c84a'))
    c.drawString(cx, cy_top - 5 * mm, '8TH EDITION  ·  LIVE IN ABUJA')

    # Divider
    c.setStrokeColor(colors.HexColor('#c9960c'))
    c.setLineWidth(0.5)
    c.line(cx, cy_top - 7 * mm, cx + 70 * mm, cy_top - 7 * mm)

    # Guest name
    c.setFillColor(colors.white)
    c.setFont('Helvetica-Bold', 9)
    guest_name = ticket.guest.full_name.upper()
    c.drawString(cx, cy_top - 13 * mm, guest_name[:32])

    # Ticket type badge
    badge_colours = {
        'REGULAR': '#555555',
        'VIP': '#8b0000',
        'VVIP': '#4b0082',
        'SPECIAL GUEST': '#005f5f',
        'SPECIAL GUEST SEAT': '#005f5f',
        'GOLD TABLE': '#c9960c',
        'MEDIA': '#1a4a00',
        'STAFF': '#1a1a1a',
    }
    ttype = ticket.ticket_type.name.upper()
    badge_color = badge_colours.get(ttype, '#333333')
    badge_x = cx
    badge_y = cy_top - 21 * mm
    badge_w = min(len(ttype) * 5.5 + 8, 65) * mm / 10
    c.setFillColor(colors.HexColor(badge_color))
    c.roundRect(badge_x, badge_y, badge_w * mm / mm, 5.5 * mm, 1.5 * mm, fill=1, stroke=0)
    c.setFillColor(colors.white)
    c.setFont('Helvetica-Bold', 7)
    c.drawCentredString(badge_x + badge_w * mm / mm / 2, badge_y + 1.5 * mm, ttype)

    # Event info rows
    row_y = cy_top - 29 * mm
    row_gap = 5 * mm
    info_rows = [
        ('DATE', ticket.event.event_date.strftime('%A, %d %B %Y').upper()),
        ('TIME', f"RED CARPET 4:00 PM  ·  MAIN EVENT 6:00 PM"),
        ('VENUE', 'A CLASS EVENT CENTER, SAPPHIRE HALL'),
        ('LOCATION', 'MAITAMA, ABUJA, FCT'),
        ('TICKET NO.', ticket.ticket_number),
    ]
    for label, value in info_rows:
        c.setFillColor(colors.HexColor('#c9960c'))
        c.setFont('Helvetica-Bold', 5.5)
        c.drawString(cx, row_y, label)
        c.setFillColor(colors.white)
        c.setFont('Helvetica', 6.5)
        c.drawString(cx + 18 * mm, row_y, value[:38])
        row_y -= row_gap

    # Instructions
    c.setFillColor(colors.HexColor('#888888'))
    c.setFont('Helvetica-Oblique', 5)
    c.drawString(cx, 6 * mm, 'Present this ticket at the entrance. This ticket is non-transferable.')

    # ── Right panel — QR code ───────────────────────────────────────────────
    qr_bytes = generate_qr_image(ticket.qr_token, size=6)
    qr_x = PAGE_W - 34 * mm
    qr_y = 12 * mm
    qr_size = 28 * mm
    c.drawImage(ImageReader(io.BytesIO(qr_bytes)), qr_x, qr_y, qr_size, qr_size)
    c.setFillColor(colors.HexColor('#888888'))
    c.setFont('Helvetica', 4.5)
    c.drawCentredString(qr_x + qr_size / 2, qr_y - 3 * mm, 'SCAN TO VERIFY')

    # Top-right: source badge
    src = 'WALK-IN' if ticket.guest.registration_source == 'WALK_IN' else 'PRE-REGISTERED'
    src_color = '#7a4200' if ticket.guest.registration_source == 'WALK_IN' else '#003a00'
    c.setFillColor(colors.HexColor(src_color))
    c.roundRect(PAGE_W - 34 * mm, PAGE_H - 15 * mm, 28 * mm, 6 * mm, 1 * mm, fill=1, stroke=0)
    c.setFillColor(colors.white)
    c.setFont('Helvetica-Bold', 5.5)
    c.drawCentredString(PAGE_W - 20 * mm, PAGE_H - 12 * mm, src)

    c.save()
    return buffer.getvalue()

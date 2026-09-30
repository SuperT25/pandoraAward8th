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

SITE_URL = 'https://pandoraaward8th.onrender.com'


def generate_qr_image(qr_token: str, size: int = 10) -> bytes:
    """
    Generate a QR code PNG.
    The QR encodes the full live verify URL so scanning opens verification directly.
    No personal data is stored in the QR.
    Returns PNG bytes.
    """
    verify_url = f"{SITE_URL}/verify/qr/{qr_token}/"

    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=size,
        border=2,
    )
    qr.add_data(verify_url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="#1a0a00", back_color="white")
    buffer = io.BytesIO()
    img.save(buffer, format='PNG')
    return buffer.getvalue()


def save_qr_to_file(ticket) -> str:
    """
    Generate and save QR PNG to media/qrcodes/<ticket_number>.png
    QR now encodes the full live verify URL.
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
    Uses pandorabg.jpeg as background.
    Returns PDF bytes.
    """
    from reportlab.lib.pagesizes import A5, landscape
    from reportlab.lib.units import mm
    from reportlab.lib import colors
    from reportlab.lib.utils import ImageReader
    from reportlab.pdfgen import canvas

    # Custom size: 210 x 99 mm (panoramic ticket format)
    PAGE_W = 210 * mm
    PAGE_H = 99 * mm

    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=(PAGE_W, PAGE_H))

    # ── Background image (pandorabg.jpeg) ───────────────────────────────────
    bg_path = os.path.join(settings.BASE_DIR, 'static', 'img', 'pandorabg.jpeg')
    if os.path.exists(bg_path):
        c.drawImage(
            ImageReader(bg_path),
            0, 0, PAGE_W, PAGE_H,
            preserveAspectRatio=False,
            mask='auto',
        )
    else:
        # Fallback solid dark background
        c.setFillColor(colors.HexColor('#0d0500'))
        c.rect(0, 0, PAGE_W, PAGE_H, fill=1, stroke=0)

    # ── Dark semi-transparent overlay so text is readable ───────────────────
    c.setFillColor(colors.HexColor('#000000'))
    c.setFillAlpha(0.62)
    c.rect(0, 0, PAGE_W, PAGE_H, fill=1, stroke=0)
    c.setFillAlpha(1.0)

    # ── Gold top stripe (BELOW the title — at bottom of header area) ────────
    # Stripe sits at top but is only 5mm — leaves room for title above it
    stripe_h = 5 * mm
    c.setFillColor(colors.HexColor('#c9960c'))
    c.rect(0, PAGE_H - stripe_h, PAGE_W, stripe_h, fill=1, stroke=0)

    # ── Gold bottom stripe ───────────────────────────────────────────────────
    c.rect(0, 0, PAGE_W, 5 * mm, fill=1, stroke=0)

    # ── HEADER — Pandora Awards title (below the gold top stripe) ───────────
    header_y = PAGE_H - stripe_h - 7 * mm

    # Left vertical gold bar accent
    c.setFillColor(colors.HexColor('#c9960c'))
    c.rect(8 * mm, PAGE_H - stripe_h - 17 * mm, 2 * mm, 13 * mm, fill=1, stroke=0)

    c.setFillColor(colors.HexColor('#c9960c'))
    c.setFont('Helvetica-Bold', 13)
    c.drawString(14 * mm, header_y, 'PANDORA AWARDS')

    c.setFillColor(colors.HexColor('#e8c84a'))
    c.setFont('Helvetica', 7)
    c.drawString(14 * mm, header_y - 5 * mm, '8TH EDITION  ·  LIVE IN ABUJA')

    # ── Horizontal gold divider ──────────────────────────────────────────────
    divider_y = PAGE_H - stripe_h - 19 * mm
    c.setStrokeColor(colors.HexColor('#c9960c'))
    c.setLineWidth(0.8)
    c.line(8 * mm, divider_y, PAGE_W - 8 * mm, divider_y)

    # ── Left panel — guest photo ─────────────────────────────────────────────
    photo_x = 8 * mm
    photo_y = 8 * mm
    photo_w = 45 * mm
    photo_h = 55 * mm

    # Photo border
    c.setStrokeColor(colors.HexColor('#c9960c'))
    c.setLineWidth(1.5)
    c.rect(photo_x, photo_y, photo_w, photo_h, fill=0, stroke=1)

    if ticket.guest.photo and hasattr(ticket.guest.photo, 'path'):
        try:
            c.drawImage(
                ImageReader(ticket.guest.photo.path),
                photo_x, photo_y, photo_w, photo_h,
                preserveAspectRatio=True, mask='auto',
            )
        except Exception:
            _draw_photo_placeholder(c, photo_x, photo_y, photo_w, photo_h)
    else:
        _draw_photo_placeholder(c, photo_x, photo_y, photo_w, photo_h)

    # ── Centre panel — guest info ────────────────────────────────────────────
    cx = 62 * mm
    name_y = divider_y - 8 * mm

    # Guest name
    c.setFillColor(colors.white)
    c.setFont('Helvetica-Bold', 11)
    guest_name = ticket.guest.full_name.upper()
    # Split long names across two lines
    if len(guest_name) > 28:
        parts = guest_name.split(' ')
        mid = len(parts) // 2
        line1 = ' '.join(parts[:mid])
        line2 = ' '.join(parts[mid:])
        c.drawString(cx, name_y, line1[:30])
        c.drawString(cx, name_y - 6 * mm, line2[:30])
        name_y -= 6 * mm
    else:
        c.drawString(cx, name_y, guest_name[:30])

    # Ticket type badge
    badge_colours = {
        'REGULAR':           '#4a4a00',
        'VIP':               '#6b0000',
        'VVIP':              '#3b0060',
        'SPECIAL GUEST':     '#004040',
        'SPECIAL GUEST SEAT':'#004040',
        'GOLD TABLE':        '#7a5a00',
        'MEDIA':             '#003a00',
        'STAFF':             '#1a1a1a',
    }
    ttype = ticket.ticket_type.name.upper()
    badge_color = badge_colours.get(ttype, '#333333')
    badge_y = name_y - 9 * mm
    badge_w = max(len(ttype) * 4.5 + 12, 30) * mm / 10
    c.setFillColor(colors.HexColor(badge_color))
    c.roundRect(cx, badge_y, badge_w * mm / mm, 6 * mm, 1.5 * mm, fill=1, stroke=0)
    # Gold border on badge
    c.setStrokeColor(colors.HexColor('#c9960c'))
    c.setLineWidth(0.5)
    c.roundRect(cx, badge_y, badge_w * mm / mm, 6 * mm, 1.5 * mm, fill=0, stroke=1)
    c.setFillColor(colors.HexColor('#c9960c'))
    c.setFont('Helvetica-Bold', 7)
    c.drawCentredString(cx + badge_w * mm / mm / 2, badge_y + 1.8 * mm, ttype)

    # Event info rows
    row_y = badge_y - 7 * mm
    row_gap = 5 * mm
    info_rows = [
        ('DATE',      ticket.event.event_date.strftime('%A, %d %B %Y').upper()),
        ('TIME',      'RED CARPET 4:00 PM  ·  MAIN EVENT 6:00 PM'),
        ('VENUE',     'A CLASS EVENT CENTER, SAPPHIRE HALL'),
        ('LOCATION',  'MAITAMA, ABUJA, FCT'),
        ('TICKET NO.', ticket.ticket_number),
    ]
    for label, value in info_rows:
        c.setFillColor(colors.HexColor('#c9960c'))
        c.setFont('Helvetica-Bold', 6)
        c.drawString(cx, row_y, label)
        c.setFillColor(colors.white)
        c.setFont('Helvetica', 7)
        c.drawString(cx + 20 * mm, row_y, value[:36])
        row_y -= row_gap

    # Instructions at bottom centre
    c.setFillColor(colors.HexColor('#aaaaaa'))
    c.setFont('Helvetica-Oblique', 5.5)
    c.drawString(cx, 7 * mm, 'Present this ticket at the entrance. This ticket is non-transferable.')

    # ── Right panel — QR code ────────────────────────────────────────────────
    qr_bytes = generate_qr_image(ticket.qr_token, size=7)
    qr_size = 32 * mm
    qr_x = PAGE_W - qr_size - 8 * mm
    qr_y = 12 * mm

    # White background for QR
    c.setFillColor(colors.white)
    c.roundRect(qr_x - 2 * mm, qr_y - 2 * mm, qr_size + 4 * mm, qr_size + 4 * mm, 2 * mm, fill=1, stroke=0)
    c.drawImage(
        ImageReader(io.BytesIO(qr_bytes)),
        qr_x, qr_y, qr_size, qr_size,
    )

    c.setFillColor(colors.HexColor('#aaaaaa'))
    c.setFont('Helvetica', 5)
    c.drawCentredString(qr_x + qr_size / 2, qr_y - 4 * mm, 'SCAN TO VERIFY')

    # ── Registration source badge (top right) ────────────────────────────────
    src = 'WALK-IN' if ticket.guest.registration_source == 'WALK_IN' else 'PRE-REGISTERED'
    src_color = '#7a4200' if ticket.guest.registration_source == 'WALK_IN' else '#004400'
    src_w = 30 * mm
    src_x = PAGE_W - src_w - 8 * mm
    src_y = PAGE_H - stripe_h - 10 * mm
    c.setFillColor(colors.HexColor(src_color))
    c.roundRect(src_x, src_y, src_w, 6 * mm, 1.5 * mm, fill=1, stroke=0)
    c.setStrokeColor(colors.HexColor('#c9960c'))
    c.setLineWidth(0.5)
    c.roundRect(src_x, src_y, src_w, 6 * mm, 1.5 * mm, fill=0, stroke=1)
    c.setFillColor(colors.white)
    c.setFont('Helvetica-Bold', 6)
    c.drawCentredString(src_x + src_w / 2, src_y + 1.8 * mm, src)

    c.save()
    return buffer.getvalue()


def _draw_photo_placeholder(c, x, y, w, h):
    from reportlab.lib import colors
    c.setFillColor(colors.HexColor('#2a1500'))
    c.rect(x, y, w, h, fill=1, stroke=0)
    c.setFillColor(colors.HexColor('#c9960c'))
    c.setFont('Helvetica', 8)
    c.drawCentredString(x + w / 2, y + h / 2, 'PHOTO')

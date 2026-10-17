"""
Pandora E-Ticket System — Utility functions
QR code generation, PDF ticket generation, IP helper
"""

import io
import os
import urllib.request
import qrcode
from django.conf import settings

SITE_URL = 'https://pandoraaward8th.onrender.com'


# ---------------------------------------------------------------------------
# IP Address helper
# ---------------------------------------------------------------------------

def get_client_ip(request):
    x_forwarded = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded:
        return x_forwarded.split(',')[-1].strip()
    return request.META.get('REMOTE_ADDR')


# ---------------------------------------------------------------------------
# QR Code generation
# ---------------------------------------------------------------------------

def generate_qr_image(qr_token: str, size: int = 8) -> bytes:
    verify_url = f"{SITE_URL}/verify/qr/{qr_token}/"
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=size,
        border=1,
    )
    qr.add_data(verify_url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    return buf.getvalue()


def save_qr_to_file(ticket) -> str:
    from django.core.files.base import ContentFile
    from django.core.files.storage import default_storage
    png = generate_qr_image(ticket.qr_token)
    path = f"qrcodes/{ticket.ticket_number}.png"
    try:
        if default_storage.exists(path):
            default_storage.delete(path)
    except Exception:
        pass
    default_storage.save(path, ContentFile(png))
    return path


# ---------------------------------------------------------------------------
# Map ticket type → background image file
# ---------------------------------------------------------------------------

TICKET_BG_MAP = {
    'REGULAR':            'regular.jpeg',
    'VIP':                'vip.jpeg',
    'SPECIAL GUEST SEAT': 'special guest.jpeg',
    'SPECIAL GUEST':      'special guest.jpeg',
    'GOLD TABLE':         'table.jpeg',
    'MEDIA':              'regular.jpeg',   # fallback
    'STAFF':              'regular.jpeg',   # fallback
}

# Ticket type → name overlay text (what shows on stub)
TICKET_STUB_LABELS = {
    'REGULAR':            'REGULAR TICKET',
    'VIP':                'VIP TICKET',
    'SPECIAL GUEST SEAT': 'SPECIAL GUEST',
    'SPECIAL GUEST':      'SPECIAL GUEST',
    'GOLD TABLE':         'TABLE FOR TEN',
    'MEDIA':              'MEDIA',
    'STAFF':              'STAFF',
}

# Ticket type → name text colour for guest name overlay
TICKET_NAME_COLORS = {
    'REGULAR':            '#1a0e00',   # dark on white bg
    'VIP':                '#c9960c',   # gold on black bg
    'SPECIAL GUEST SEAT': '#c9960c',   # gold on green bg
    'SPECIAL GUEST':      '#c9960c',
    'GOLD TABLE':         '#c9960c',   # gold on dark purple bg
    'MEDIA':              '#1a0e00',
    'STAFF':              '#1a0e00',
}


# ---------------------------------------------------------------------------
# PDF Ticket — uses pre-designed background images, overlays dynamic text
# Layout exactly matches the 4 reference ticket designs
# Size: A4 landscape = 297 x 210 mm (matches widescreen ticket proportions)
# ---------------------------------------------------------------------------

def generate_ticket_pdf(ticket) -> bytes:
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.units import mm
    from reportlab.lib import colors
    from reportlab.lib.utils import ImageReader
    from reportlab.pdfgen import canvas

    PAGE_W, PAGE_H = landscape(A4)   # 297 x 210 mm

    ttype = ticket.ticket_type.name.upper()
    bg_file = TICKET_BG_MAP.get(ttype, 'regular.jpeg')
    bg_path = os.path.join(settings.BASE_DIR, 'static', 'img', bg_file)

    name_color = colors.HexColor(TICKET_NAME_COLORS.get(ttype, '#1a0e00'))
    GOLD       = colors.HexColor('#c9960c')
    WHITE      = colors.white
    BLACK      = colors.black

    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=(PAGE_W, PAGE_H))

    # ── Full background image ────────────────────────────────────────
    if os.path.exists(bg_path):
        c.drawImage(
            ImageReader(bg_path),
            0, 0, PAGE_W, PAGE_H,
            preserveAspectRatio=False,
            mask='auto',
        )
    else:
        # Fallback plain background
        c.setFillColor(colors.HexColor('#f5f0e8'))
        c.rect(0, 0, PAGE_W, PAGE_H, fill=1, stroke=0)

    # ════════════════════════════════════════════════════════════════
    # GUEST NAME — cover the baked-in sample name first, then
    # write the real guest name cleanly on top
    # ════════════════════════════════════════════════════════════════

    guest_name = ticket.guest.full_name

    # Cover rectangle dimensions — covers the name area in the bg image
    # Position varies slightly per ticket type but is roughly:
    # x: 18mm, y: 18mm from bottom, width: 55% of page, height: 22mm
    cover_colors = {
        'REGULAR':            '#e8e0d0',   # cream/off-white (matches Regular bg)
        'VIP':                '#0a0a0a',   # near-black (matches VIP bg)
        'SPECIAL GUEST SEAT': '#1a3a1a',   # dark green (matches Special Guest bg)
        'SPECIAL GUEST':      '#1a3a1a',
        'GOLD TABLE':         '#1a0a28',   # dark purple (matches Gold Table bg)
        'MEDIA':              '#e8e0d0',
        'STAFF':              '#e8e0d0',
    }
    cover_hex = cover_colors.get(ttype, '#1a0a0a')
    c.setFillColor(colors.HexColor(cover_hex))
    c.rect(18 * mm, 16 * mm, PAGE_W * 0.58, 24 * mm, fill=1, stroke=0)

    # Now write the real guest name
    if len(guest_name) <= 20:
        name_font_size = 28
    elif len(guest_name) <= 28:
        name_font_size = 22
    else:
        name_font_size = 18

    c.setFillColor(name_color)
    c.setFont('Helvetica-BoldOblique', name_font_size)
    c.drawString(22 * mm, 24 * mm, guest_name[:35])

    # ════════════════════════════════════════════════════════════════
    # QR CODE — cover the baked-in barcode first, then draw real QR
    # ════════════════════════════════════════════════════════════════

    stub_x = PAGE_W * 0.755
    stub_w = PAGE_W - stub_x

    # Cover the baked-in barcode area on the stub
    # The barcode in the images sits roughly in the upper-middle of stub
    barcode_cover_colors = {
        'REGULAR':            '#f5f0e8',   # light cream
        'VIP':                '#0a0a0a',   # black
        'SPECIAL GUEST SEAT': '#1a3a1a',   # dark green
        'SPECIAL GUEST':      '#1a3a1a',
        'GOLD TABLE':         '#1a0a28',   # dark purple
        'MEDIA':              '#f5f0e8',
        'STAFF':              '#f5f0e8',
    }
    bc_cover = barcode_cover_colors.get(ttype, '#0a0a0a')
    cover_w = stub_w - 8 * mm
    cover_x = stub_x + 4 * mm
    # Cover from y=55mm to y=120mm from bottom (barcode + surrounding area)
    c.setFillColor(colors.HexColor(bc_cover))
    c.rect(cover_x, 55 * mm, cover_w, 65 * mm, fill=1, stroke=0)

    # Now draw the real QR code
    qr_bytes = generate_qr_image(ticket.qr_token, size=6)
    qr_sz = 34 * mm
    qr_x = stub_x + (stub_w - qr_sz) / 2
    qr_y = PAGE_H / 2 - qr_sz / 2 - 5 * mm

    # White background for QR
    c.setFillColor(colors.white)
    c.roundRect(qr_x - 2*mm, qr_y - 2*mm, qr_sz + 4*mm, qr_sz + 4*mm,
                2*mm, fill=1, stroke=0)
    c.drawImage(
        ImageReader(io.BytesIO(qr_bytes)),
        qr_x, qr_y, qr_sz, qr_sz,
    )

    # Ticket number under QR
    c.setFillColor(colors.black)
    c.setFont('Helvetica-Bold', 7.5)
    c.drawCentredString(
        stub_x + stub_w / 2,
        qr_y - 5 * mm,
        ticket.ticket_number,
    )

    c.save()
    return buf.getvalue()


def _draw_photo_placeholder(c, x, y, w, h):
    from reportlab.lib import colors as _colors
    c.setFillColor(_colors.HexColor('#eeeeee'))
    c.rect(x, y, w, h, fill=1, stroke=0)
    c.setFillColor(_colors.HexColor('#999999'))
    c.setFont('Helvetica', 7)
    c.drawCentredString(x + w / 2, y + h / 2, 'PHOTO')

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
# Ticket type → background image + text colour
# New clean images: no sample name, no barcode — ready for overlay
# ---------------------------------------------------------------------------

TICKET_CONFIG = {
    'REGULAR': {
        'bg':         'reg.jpeg',
        'name_color': '#1a0e00',
        'name_x':     22,
        'name_y':     28,
        'qr_center_x_pct': 0.875,
        'qr_center_y_mm':  78,
        'qr_size_mm':      28,
    },
    'VIP': {
        'bg':         'VIP.jpeg',
        'name_color': '#c9960c',
        'name_x':     22,
        'name_y':     28,
        'qr_center_x_pct': 0.875,
        'qr_center_y_mm':  78,
        'qr_size_mm':      28,
    },
    'SPECIAL GUEST SEAT': {
        'bg':         'special.jpeg',
        'name_color': '#c9960c',
        'name_x':     22,
        'name_y':     28,
        'qr_center_x_pct': 0.875,
        'qr_center_y_mm':  78,
        'qr_size_mm':      28,
    },
    'SPECIAL GUEST': {
        'bg':         'special.jpeg',
        'name_color': '#c9960c',
        'name_x':     22,
        'name_y':     28,
        'qr_center_x_pct': 0.875,
        'qr_center_y_mm':  78,
        'qr_size_mm':      28,
    },
    'GOLD TABLE': {
        'bg':         'table.jpeg',
        'name_color': '#c9960c',
        'name_x':     22,
        'name_y':     28,
        'qr_center_x_pct': 0.875,
        'qr_center_y_mm':  78,
        'qr_size_mm':      28,
    },
    'TABLE OF TEN': {
        'bg':         'table.jpeg',
        'name_color': '#c9960c',
        'name_x':     22,
        'name_y':     28,
        'qr_center_x_pct': 0.875,
        'qr_center_y_mm':  78,
        'qr_size_mm':      28,
    },
    'MEDIA': {
        'bg':         'reg.jpeg',
        'name_color': '#1a0e00',
        'name_x':     22,
        'name_y':     28,
        'qr_center_x_pct': 0.875,
        'qr_center_y_mm':  78,
        'qr_size_mm':      28,
    },
    'STAFF': {
        'bg':         'reg.jpeg',
        'name_color': '#1a0e00',
        'name_x':     22,
        'name_y':     28,
        'qr_center_x_pct': 0.875,
        'qr_center_y_mm':  78,
        'qr_size_mm':      28,
    },
}

DEFAULT_CONFIG = TICKET_CONFIG['REGULAR']


# ---------------------------------------------------------------------------
# PDF Ticket — uses clean background images, overlays name + QR
# Size: A4 landscape = 297 x 210 mm
# ---------------------------------------------------------------------------

def generate_ticket_pdf(ticket) -> bytes:
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.units import mm
    from reportlab.lib import colors
    from reportlab.lib.utils import ImageReader
    from reportlab.pdfgen import canvas

    PAGE_W, PAGE_H = landscape(A4)   # 297 x 210 mm

    ttype = ticket.ticket_type.name.upper()
    cfg = TICKET_CONFIG.get(ttype, DEFAULT_CONFIG)

    bg_path = os.path.join(settings.BASE_DIR, 'static', 'img', cfg['bg'])
    name_color = colors.HexColor(cfg['name_color'])

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
        c.setFillColor(colors.HexColor('#f5f0e8'))
        c.rect(0, 0, PAGE_W, PAGE_H, fill=1, stroke=0)

    # ════════════════════════════════════════════════════════════════
    # GUEST NAME — placed in the blank TICKET HOLDER area
    # The background has "TICKET HOLDER" label — name goes below it
    # ════════════════════════════════════════════════════════════════

    guest_name = ticket.guest.full_name.upper()  # UPPERCASE like reference

    # Font size based on name length
    if len(guest_name) <= 16:
        name_size = 32
    elif len(guest_name) <= 22:
        name_size = 26
    elif len(guest_name) <= 30:
        name_size = 22
    else:
        name_size = 18

    c.setFillColor(name_color)
    c.setFont('Helvetica-Bold', name_size)   # Bold, not italic
    c.drawString(
        cfg['name_x'] * mm,
        cfg['name_y'] * mm,
        guest_name[:40],
    )

    # ════════════════════════════════════════════════════════════════
    # QR CODE — placed inside the white square box on the stub
    # ════════════════════════════════════════════════════════════════

    qr_sz = cfg['qr_size_mm'] * mm
    qr_cx = PAGE_W * cfg['qr_center_x_pct']
    qr_cy = cfg['qr_center_y_mm'] * mm

    qr_x = qr_cx - qr_sz / 2
    qr_y = qr_cy - qr_sz / 2

    qr_bytes = generate_qr_image(ticket.qr_token, size=6)
    c.drawImage(
        ImageReader(io.BytesIO(qr_bytes)),
        qr_x, qr_y, qr_sz, qr_sz,
    )

    # Ticket number below QR
    c.setFillColor(colors.HexColor(cfg['name_color']))
    c.setFont('Helvetica-Bold', 7)
    c.drawCentredString(
        qr_cx,
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

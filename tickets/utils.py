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

# ── Ticket physical dimensions ───────────────────────────────────────────────
# Full ticket : 8.0 × 3.0 inches at 300 DPI
# Stub        : rightmost ~2.0 inches (25 % of width)
# QR code     : 1.2 × 1.2 inches, centred in stub QR box
#
# ReportLab works in points (1 pt = 1/72 inch)
PT  = 1.0            # 1 point
IN  = 72.0           # points per inch

TICKET_W = 8.0 * IN   # 576 pt
TICKET_H = 3.0 * IN   # 216 pt

# Stub occupies the right 25 % (~2 in) of the ticket
STUB_X_PCT  = 0.755    # stub left edge
STUB_W_PCT  = 0.245    # stub width

# QR placeholder centre inside the gold-bordered box on stub
# x: ~84% of ticket width (inside stub, not too far right)
# y: ~50% of ticket height (middle of stub between category and SCAN TO VALIDATE)
# QR placeholder — rectangular box, 226 × 185 px on 1536 × 864 px image
# Box top-left: (1205, 432)  Centre: (1318, 524.5 px)
# X%: 1318/1536 = 85.8%   Y from bottom: (864-524.5)/864 = 39.3%
# Box dimensions in inches: 226/192=1.177in wide, 185/288=0.642in tall
# (1536px/8in = 192 DPI horizontal, 864px/3in = 288 DPI vertical)
QR_CX_PCT   = 0.858
QR_CY_PCT   = 0.393
QR_W_IN     = 1.177   # width to fill box exactly
QR_H_IN     = 0.642   # height to fill box exactly
QR_W_PT     = QR_W_IN * IN
QR_H_PT     = QR_H_IN * IN
# Keep backward compat
QR_SIZE_PT  = QR_W_PT

# Guest name strip (TICKET HOLDER area)
# x: ~14% from left   y: ~14% from bottom (inside the strip, not outside)
NAME_X_PCT  = 0.14
NAME_Y_PCT  = 0.14    # % from BOTTOM


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

def generate_qr_image(qr_token: str, size: int = 10) -> bytes:
    """Generate QR PNG encoding the full live verify URL."""
    verify_url = f"{SITE_URL}/verify/qr/{qr_token}/"
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=size,
        border=2,
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
# Ticket type → background PNG + name text colour
# ---------------------------------------------------------------------------

TICKET_CONFIG = {
    'REGULAR': {
        'bg':         'REGULAR (1).PNG',
        'name_color': '#1a0e00',
        # QR box: 226×185px on 1536×864. Top-left:(1205,432). Centre:(1318,524.5)
        # DPI: 192h × 288v
        'qr_cx_pct':  0.858,
        'qr_cy_pct':  0.393,
        'qr_w_in':    1.177,
        'qr_h_in':    0.642,
    },
    'VIP': {
        'bg':         'VIP.PNG',
        'name_color': '#c9960c',
        'name_font_max': 11,
        # QR box pixel-verified: (1667,353)->(1925,520) on 2046x768 image
        # cx=0.8778, cy_from_bottom=0.4323, max square=0.652in
        'qr_cx_pct':  0.8778,
        'qr_cy_pct':  0.4323,
        'qr_w_in':    0.652,
        'qr_h_in':    0.652,
    },
    'SPECIAL GUEST SEAT': {
        'bg':         'SPECIAL .PNG',
        'name_color': '#c9960c',
        'name_font_max': 11,
        # QR box pixel-verified: (1313,419)->(1585,673) on 1671x941 image
        # cx=0.8671, cy_from_bottom=0.4198, max square=0.810in
        'qr_cx_pct':  0.8671,
        'qr_cy_pct':  0.4198,
        'qr_w_in':    0.810,
        'qr_h_in':    0.810,
    },
    'SPECIAL GUEST': {
        'bg':         'SPECIAL .PNG',
        'name_color': '#c9960c',
        'name_font_max': 11,
        'qr_cx_pct':  0.8671,
        'qr_cy_pct':  0.4198,
        'qr_w_in':    0.810,
        'qr_h_in':    0.810,
    },
    'TABLE OF TEN': {
        'bg':         'TABLE OF TEN.PNG',
        'name_color': '#c9960c',
        'name_font_max': 11,
        # QR box pixel-verified: (1258,432)->(1590,657) on 1672x941 image
        # cx=0.8517, cy_from_bottom=0.4219, max square=0.717in
        'qr_cx_pct':  0.8517,
        'qr_cy_pct':  0.4219,
        'qr_w_in':    0.717,
        'qr_h_in':    0.717,
    },
    'GOLD TABLE': {
        'bg':         'TABLE OF TEN.PNG',
        'name_color': '#c9960c',
        'name_font_max': 11,
        'qr_cx_pct':  0.8517,
        'qr_cy_pct':  0.4219,
        'qr_w_in':    0.717,
        'qr_h_in':    0.717,
    },
    'MEDIA': {
        'bg':         'REGULAR (1).PNG',
        'name_color': '#1a0e00',
        'qr_cx_pct':  0.858,
        'qr_cy_pct':  0.393,
        'qr_w_in':    1.177,
        'qr_h_in':    0.642,
    },
    'STAFF': {
        'bg':         'REGULAR (1).PNG',
        'name_color': '#1a0e00',
        'qr_cx_pct':  0.858,
        'qr_cy_pct':  0.393,
        'qr_w_in':    1.177,
        'qr_h_in':    0.642,
    },
}

DEFAULT_CONFIG = TICKET_CONFIG['REGULAR']


# ---------------------------------------------------------------------------
# Photo loader helper
# ---------------------------------------------------------------------------

def _get_photo_reader(photo_field):
    from reportlab.lib.utils import ImageReader
    if not photo_field:
        return None
    try:
        url = photo_field.url
        if url.startswith('http'):
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=10) as r:
                return ImageReader(io.BytesIO(r.read()))
        else:
            return ImageReader(photo_field.path)
    except Exception:
        return None


# ---------------------------------------------------------------------------
# PDF Ticket generator
#
# Layout (all measurements in ReportLab points, y=0 at bottom-left):
#
#   ┌─────────────────────────────────┬──────────┐
#   │  MAIN PANEL  (75 %)             │  STUB    │
#   │                                 │ (25 %)   │
#   │  [logo] PANDORA AWARDS title    │ [logo]   │
#   │  ticket-type box | price box    │ category │
#   │  date / time / venue row        │          │
#   │  ──────────────────────────     │ [QR BOX] │
#   │  TICKET HOLDER | _blank_        │          │
#   │                                 │ ADMIT    │
#   │  [GUEST NAME overlaid here]     │ 8TH ED.  │
#   └─────────────────────────────────┴──────────┘
# ---------------------------------------------------------------------------

def generate_ticket_pdf(ticket) -> bytes:
    from reportlab.lib.units import inch
    from reportlab.lib import colors
    from reportlab.lib.utils import ImageReader
    from reportlab.pdfgen import canvas

    ttype = ticket.ticket_type.name.upper()
    cfg   = TICKET_CONFIG.get(ttype, DEFAULT_CONFIG)

    bg_path    = os.path.join(settings.BASE_DIR, 'static', 'img', cfg['bg'])
    name_color = colors.HexColor(cfg['name_color'])

    # Per-ticket QR box settings
    qr_cx_pct = cfg.get('qr_cx_pct', QR_CX_PCT)
    qr_cy_pct = cfg.get('qr_cy_pct', QR_CY_PCT)
    qr_w_pt   = cfg.get('qr_w_in', 1.177) * IN
    qr_h_pt   = cfg.get('qr_h_in', 0.642) * IN

    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=(TICKET_W, TICKET_H))

    # ── 1. Full-page background PNG ──────────────────────────────────────
    if os.path.exists(bg_path):
        c.drawImage(
            ImageReader(bg_path),
            0, 0, TICKET_W, TICKET_H,
            preserveAspectRatio=False,
            mask='auto',
        )
    else:
        # Fallback plain bg
        c.setFillColor(colors.HexColor('#f5f0e8'))
        c.rect(0, 0, TICKET_W, TICKET_H, fill=1, stroke=0)

    # ── 2. Guest name overlay (TICKET HOLDER strip) ─────────────────────
    # The TICKET HOLDER strip sits near the bottom of the main panel.
    # Measured from images: x ≈ 12 %, y ≈ 18-22 % from bottom.
    guest_name = ticket.guest.full_name.upper()

    # Use per-ticket max font size (Regular keeps 13pt, others use 11pt)
    max_pt = cfg.get('name_font_max', 13)
    if   len(guest_name) <= 16: name_pt = max_pt
    elif len(guest_name) <= 22: name_pt = max_pt - 2
    elif len(guest_name) <= 30: name_pt = max_pt - 4
    else:                        name_pt = max_pt - 5

    name_x = TICKET_W * NAME_X_PCT
    name_y = TICKET_H * NAME_Y_PCT

    c.setFillColor(name_color)
    c.setFont('Helvetica-Bold', name_pt)
    c.drawString(name_x, name_y, guest_name[:40])

    # ── 3. QR code overlay (stub QR placeholder box) ────────────────────
    # The gold-bordered empty box on the stub.
    # Centre: x ≈ 87.5 % of ticket width, y ≈ 50 % of ticket height.
    qr_cx = TICKET_W * qr_cx_pct
    qr_cy = TICKET_H * qr_cy_pct
    qr_x  = qr_cx - qr_w_pt / 2
    qr_y  = qr_cy - qr_h_pt / 2

    qr_bytes = generate_qr_image(ticket.qr_token, size=10)
    c.drawImage(
        ImageReader(io.BytesIO(qr_bytes)),
        qr_x, qr_y,
        qr_w_pt, qr_h_pt,
    )

    c.save()
    return buf.getvalue()


def _draw_photo_placeholder(c, x, y, w, h):
    from reportlab.lib import colors as _c
    c.setFillColor(_c.HexColor('#eeeeee'))
    c.rect(x, y, w, h, fill=1, stroke=0)

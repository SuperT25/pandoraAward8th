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
    # QR encodes the full verify URL so phone camera opens it directly
    verify_url = f"{SITE_URL}/verify/qr/{qr_token}/"
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=size,
        border=1,
    )
    qr.add_data(verify_url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="#0d2818", back_color="white")
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
# Load photo — works with Cloudinary (http URL) and local storage
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
# PDF Ticket — Premium redesign
# Size: 180 x 72 mm  (compact boarding-pass style)
# ---------------------------------------------------------------------------

def generate_ticket_pdf(ticket) -> bytes:
    from reportlab.lib.units import mm
    from reportlab.lib import colors
    from reportlab.lib.utils import ImageReader
    from reportlab.pdfgen import canvas
    from reportlab.pdfbase import pdfmetrics

    # ── Canvas ──────────────────────────────────────────────────────────────
    W = 180 * mm
    H = 72  * mm

    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=(W, H))

    # ── Colours ─────────────────────────────────────────────────────────────
    GREEN      = colors.HexColor('#0d2818')
    GREEN_MID  = colors.HexColor('#1a4a2a')
    GOLD       = colors.HexColor('#c9960c')
    GOLD_LT    = colors.HexColor('#e8c84a')
    CREAM      = colors.HexColor('#faf6ee')
    WHITE      = colors.white
    BLACK      = colors.HexColor('#111111')
    GREY       = colors.HexColor('#666666')
    LGREY      = colors.HexColor('#999999')

    # ── Panel widths ─────────────────────────────────────────────────────────
    LP = 42 * mm   # left panel
    RP = 28 * mm   # right panel
    MP = W - LP - RP  # centre ~110 mm

    # ════════════════════════════════════════════════════════════════
    # BACKGROUND — full cream base
    # ════════════════════════════════════════════════════════════════
    c.setFillColor(CREAM)
    c.rect(0, 0, W, H, fill=1, stroke=0)

    # ════════════════════════════════════════════════════════════════
    # LEFT PANEL
    # ════════════════════════════════════════════════════════════════
    # Dark green fill
    c.setFillColor(GREEN)
    c.rect(0, 0, LP, H, fill=1, stroke=0)

    # Subtle gold diagonal shimmer
    c.saveState()
    c.setStrokeColor(colors.HexColor('#c9960c'))
    c.setLineWidth(0.4)
    c.setStrokeAlpha(0.25)
    for i in range(-4, 12):
        c.line(i * 8 * mm, 0, i * 8 * mm + H, H)
    c.restoreState()

    # Gold top bar
    c.setFillColor(GOLD)
    c.rect(0, H - 3 * mm, LP, 3 * mm, fill=1, stroke=0)

    # Gold bottom bar
    c.rect(0, 0, LP, 3 * mm, fill=1, stroke=0)

    # Logo
    logo_path = os.path.join(settings.BASE_DIR, 'static', 'img', 'pandora-logo.jpeg')
    if os.path.exists(logo_path):
        lsz = 28 * mm
        lx  = (LP - lsz) / 2
        ly  = H / 2 - lsz / 2 + 2 * mm
        c.drawImage(ImageReader(logo_path), lx, ly, lsz, lsz,
                    preserveAspectRatio=True, mask='auto')

    # "Celebrating Excellence"
    c.setFillColor(GOLD_LT)
    c.setFont('Helvetica-Oblique', 5)
    c.drawCentredString(LP / 2, 5 * mm, 'Celebrating Excellence')

    # ════════════════════════════════════════════════════════════════
    # RIGHT PANEL
    # ════════════════════════════════════════════════════════════════
    rx = LP + MP
    c.setFillColor(GREEN)
    c.rect(rx, 0, RP, H, fill=1, stroke=0)

    # Same shimmer
    c.saveState()
    c.setStrokeColor(colors.HexColor('#c9960c'))
    c.setLineWidth(0.4)
    c.setStrokeAlpha(0.25)
    for i in range(-2, 8):
        c.line(rx + i * 8 * mm, 0, rx + i * 8 * mm + H, H)
    c.restoreState()

    # Gold bars
    c.setFillColor(GOLD)
    c.rect(rx, H - 3 * mm, RP, 3 * mm, fill=1, stroke=0)
    c.rect(rx, 0, RP, 3 * mm, fill=1, stroke=0)

    # QR code
    qr_bytes = generate_qr_image(ticket.qr_token, size=5)
    qsz = 20 * mm
    qx  = rx + (RP - qsz) / 2
    qy  = H / 2 - qsz / 2 + 3 * mm

    # White rounded bg for QR
    c.setFillColor(WHITE)
    c.roundRect(qx - 1.5*mm, qy - 1.5*mm, qsz + 3*mm, qsz + 3*mm, 1*mm, fill=1, stroke=0)
    c.drawImage(ImageReader(io.BytesIO(qr_bytes)), qx, qy, qsz, qsz)

    c.setFillColor(GOLD_LT)
    c.setFont('Helvetica-Bold', 4.5)
    c.drawCentredString(rx + RP / 2, qy - 3 * mm, 'SCAN TO VERIFY')

    # "Celebrating Excellence"
    c.setFillColor(GOLD_LT)
    c.setFont('Helvetica-Oblique', 5)
    c.drawCentredString(rx + RP / 2, 5 * mm, 'Celebrating Excellence')

    # ════════════════════════════════════════════════════════════════
    # PERFORATED DIVIDERS (dashed lines between panels)
    # ════════════════════════════════════════════════════════════════
    c.saveState()
    c.setStrokeColor(colors.HexColor('#cccccc'))
    c.setLineWidth(0.5)
    c.setDash(2, 3)
    c.line(LP, 3 * mm, LP, H - 3 * mm)
    c.line(rx, 3 * mm, rx, H - 3 * mm)
    c.restoreState()

    # Semicircle notches on dividers
    for notch_x in [LP, rx]:
        c.setFillColor(CREAM)
        c.circle(notch_x, H - 3 * mm, 2.5 * mm, fill=1, stroke=0)
        c.circle(notch_x, 3 * mm,     2.5 * mm, fill=1, stroke=0)

    # ════════════════════════════════════════════════════════════════
    # CENTRE PANEL
    # ════════════════════════════════════════════════════════════════
    mx = LP

    # Faint watermark logo
    if os.path.exists(logo_path):
        wsz = 40 * mm
        wx  = mx + (MP - wsz) / 2
        wy  = (H - wsz) / 2
        c.saveState()
        c.setFillAlpha(0.05)
        c.drawImage(ImageReader(logo_path), wx, wy, wsz, wsz,
                    preserveAspectRatio=True, mask='auto')
        c.restoreState()

    # Gold top + bottom bars on centre
    c.setFillColor(GOLD)
    c.rect(mx, H - 3 * mm, MP, 3 * mm, fill=1, stroke=0)
    c.rect(mx, 0, MP, 3 * mm, fill=1, stroke=0)

    # ── Header ───────────────────────────────────────────────────────
    ht = H - 3 * mm - 4.5 * mm   # top of text area

    c.setFillColor(GREY)
    c.setFont('Helvetica', 5)
    c.drawCentredString(mx + MP / 2, ht, 'PANDORA AWARDS  ·  8TH EDITION  ·  ABUJA 2026')

    c.setFillColor(BLACK)
    c.setFont('Helvetica-Bold', 9.5)
    c.drawCentredString(mx + MP / 2, ht - 5.5 * mm, 'PANDORA AWARD 8TH EDITION E-TICKET')

    # Gold thin divider
    c.setStrokeColor(GOLD)
    c.setLineWidth(0.6)
    c.line(mx + 4*mm, ht - 7*mm, mx + MP - 4*mm, ht - 7*mm)

    # ── Guest name — large and prominent ─────────────────────────────
    gname = ticket.guest.full_name.upper()
    c.setFillColor(BLACK)
    # Shrink font if name is long
    fname_size = 9 if len(gname) <= 22 else 7.5
    c.setFont('Helvetica-Bold', fname_size)
    c.drawCentredString(mx + MP / 2, ht - 11.5 * mm, gname[:32])

    # Ticket type pill
    ttype = ticket.ticket_type.name.upper()
    pill_w = max(len(ttype) * 3.2 + 8, 20) * mm / 10
    pill_x = mx + MP / 2 - pill_w / 2
    pill_y = ht - 16.5 * mm
    c.setFillColor(GREEN)
    c.roundRect(pill_x, pill_y, pill_w, 4.5 * mm, 2 * mm, fill=1, stroke=0)
    c.setStrokeColor(GOLD)
    c.setLineWidth(0.4)
    c.roundRect(pill_x, pill_y, pill_w, 4.5 * mm, 2 * mm, fill=0, stroke=1)
    c.setFillColor(GOLD)
    c.setFont('Helvetica-Bold', 5.5)
    c.drawCentredString(mx + MP / 2, pill_y + 1.3 * mm, ttype)

    # ── Two-column info grid ──────────────────────────────────────────
    c1x = mx + 4 * mm
    c2x = mx + MP / 2 + 2 * mm
    gy  = ht - 23 * mm
    gap = 8 * mm

    def cell(x, y, label, val, chars=22):
        c.setFillColor(GOLD)
        c.setFont('Helvetica-Bold', 4.5)
        c.drawString(x, y, label)
        c.setFillColor(BLACK)
        c.setFont('Helvetica', 6)
        c.drawString(x, y - 3.5 * mm, str(val)[:chars])

    # Row 1
    cell(c1x, gy,       'FULL NAME',    ticket.guest.full_name)
    cell(c2x, gy,       'EVENT DATE',   ticket.event.event_date.strftime('%A, %d %B %Y'))

    # Row 2
    cell(c1x, gy - gap, 'PHONE',        ticket.guest.phone_number)
    cell(c2x, gy - gap, 'TIME',         'Red Carpet 4PM  ·  Main Event 6PM')

    # Row 3
    cell(c1x, gy - gap*2, 'TICKET NO.', ticket.ticket_number, chars=18)
    cell(c2x, gy - gap*2, 'VENUE',      'A Class Event Center, Sapphire Hall', chars=28)

    # ── Bottom strip — thin gold line + instruction ───────────────────
    c.setStrokeColor(GOLD)
    c.setLineWidth(0.4)
    c.line(mx + 4*mm, 5*mm, mx + MP - 4*mm, 5*mm)

    c.setFillColor(LGREY)
    c.setFont('Helvetica-Oblique', 4.5)
    c.drawCentredString(mx + MP / 2, 3.8 * mm,
        'This ticket is non-transferable. Present at entrance for verification.')

    c.save()
    return buf.getvalue()


def _draw_photo_placeholder(c, x, y, w, h):
    from reportlab.lib import colors
    c.setFillColor(colors.HexColor('#1a3a20'))
    c.rect(x, y, w, h, fill=1, stroke=0)
    c.setFillColor(colors.HexColor('#c9960c'))
    c.setFont('Helvetica', 7)
    c.drawCentredString(x + w / 2, y + h / 2, 'PHOTO')

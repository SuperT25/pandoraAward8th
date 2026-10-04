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
# Photo loader — works with Cloudinary (http) and local storage
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
# Ticket type theme definitions
# ---------------------------------------------------------------------------

TICKET_THEMES = {
    'REGULAR': {
        'panel':      '#1a1a2e',   # Dark navy
        'panel2':     '#16213e',
        'accent':     '#a0a0b0',   # Silver
        'accent_lt':  '#d0d0e0',
        'badge_bg':   '#2a2a4a',
        'label':      'REGULAR',
        'price':      '₦30,000',
        'qr_fill':    '#1a1a2e',
    },
    'VIP': {
        'panel':      '#4a0000',   # Deep red
        'panel2':     '#3a0000',
        'accent':     '#c9960c',   # Gold
        'accent_lt':  '#e8c84a',
        'badge_bg':   '#6a0000',
        'label':      'VIP',
        'price':      '₦100,000',
        'qr_fill':    '#4a0000',
    },
    'SPECIAL GUEST SEAT': {
        'panel':      '#0d2818',   # Deep green
        'panel2':     '#0a1f12',
        'accent':     '#c9960c',   # Gold
        'accent_lt':  '#e8c84a',
        'badge_bg':   '#1a4a28',
        'label':      'SPECIAL GUEST',
        'price':      '₦300,000',
        'qr_fill':    '#0d2818',
    },
    'SPECIAL GUEST': {
        'panel':      '#0d2818',
        'panel2':     '#0a1f12',
        'accent':     '#c9960c',
        'accent_lt':  '#e8c84a',
        'badge_bg':   '#1a4a28',
        'label':      'SPECIAL GUEST',
        'price':      '₦300,000',
        'qr_fill':    '#0d2818',
    },
    'GOLD TABLE': {
        'panel':      '#1a0e00',   # Near black
        'panel2':     '#0d0700',
        'accent':     '#c9960c',   # Full gold
        'accent_lt':  '#f0d060',
        'badge_bg':   '#3a2800',
        'label':      'GOLD TABLE',
        'price':      '₦800,000',
        'qr_fill':    '#1a0e00',
    },
    'MEDIA': {
        'panel':      '#001a2e',
        'panel2':     '#00111e',
        'accent':     '#4ab0ff',
        'accent_lt':  '#a0d8ff',
        'badge_bg':   '#002a4a',
        'label':      'MEDIA',
        'price':      'PRESS',
        'qr_fill':    '#001a2e',
    },
    'STAFF': {
        'panel':      '#1a1a1a',
        'panel2':     '#111111',
        'accent':     '#888888',
        'accent_lt':  '#bbbbbb',
        'badge_bg':   '#2a2a2a',
        'label':      'STAFF',
        'price':      'CREW',
        'qr_fill':    '#1a1a1a',
    },
}

DEFAULT_THEME = TICKET_THEMES['REGULAR']


def get_theme(ticket_type_name: str) -> dict:
    return TICKET_THEMES.get(ticket_type_name.upper(), DEFAULT_THEME)


# ---------------------------------------------------------------------------
# PDF Ticket — 180 x 72 mm, type-differentiated design
# ---------------------------------------------------------------------------

def generate_ticket_pdf(ticket) -> bytes:
    from reportlab.lib.units import mm
    from reportlab.lib import colors
    from reportlab.lib.utils import ImageReader
    from reportlab.pdfgen import canvas

    W = 180 * mm
    H = 72  * mm

    theme = get_theme(ticket.ticket_type.name)

    # Colour palette from theme
    PANEL   = colors.HexColor(theme['panel'])
    PANEL2  = colors.HexColor(theme['panel2'])
    ACCENT  = colors.HexColor(theme['accent'])
    ACCENTL = colors.HexColor(theme['accent_lt'])
    BADGEBG = colors.HexColor(theme['badge_bg'])
    WHITE   = colors.white
    CREAM   = colors.HexColor('#faf6ee')
    BLACK   = colors.HexColor('#111111')
    GREY    = colors.HexColor('#555555')
    LGREY   = colors.HexColor('#999999')

    LP = 42 * mm
    RP = 28 * mm
    MP = W - LP - RP

    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=(W, H))

    # ── Cream base ───────────────────────────────────────────────────
    c.setFillColor(CREAM)
    c.rect(0, 0, W, H, fill=1, stroke=0)

    # ════════════════════════════════════════════════════════════════
    # LEFT PANEL
    # ════════════════════════════════════════════════════════════════
    c.setFillColor(PANEL)
    c.rect(0, 0, LP, H, fill=1, stroke=0)

    # Subtle shimmer lines
    c.saveState()
    c.setStrokeColor(ACCENT)
    c.setLineWidth(0.3)
    c.setStrokeAlpha(0.2)
    for i in range(-3, 10):
        c.line(i * 9 * mm, 0, i * 9 * mm + H, H)
    c.restoreState()

    # Accent top + bottom bars
    c.setFillColor(ACCENT)
    c.rect(0, H - 3 * mm, LP, 3 * mm, fill=1, stroke=0)
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
    c.setFillColor(ACCENTL)
    c.setFont('Helvetica-Oblique', 5)
    c.drawCentredString(LP / 2, 5 * mm, 'Celebrating Excellence')

    # Ticket type label on left panel bottom
    c.setFillColor(BADGEBG)
    c.roundRect(3 * mm, 8.5 * mm, LP - 6 * mm, 5 * mm, 1.5 * mm, fill=1, stroke=0)
    c.setFillColor(ACCENT)
    c.setFont('Helvetica-Bold', 6)
    c.drawCentredString(LP / 2, 9.8 * mm, theme['label'])

    # ════════════════════════════════════════════════════════════════
    # RIGHT PANEL
    # ════════════════════════════════════════════════════════════════
    rx = LP + MP
    c.setFillColor(PANEL)
    c.rect(rx, 0, RP, H, fill=1, stroke=0)

    # Shimmer
    c.saveState()
    c.setStrokeColor(ACCENT)
    c.setLineWidth(0.3)
    c.setStrokeAlpha(0.2)
    for i in range(-2, 7):
        c.line(rx + i * 9 * mm, 0, rx + i * 9 * mm + H, H)
    c.restoreState()

    # Accent bars
    c.setFillColor(ACCENT)
    c.rect(rx, H - 3 * mm, RP, 3 * mm, fill=1, stroke=0)
    c.rect(rx, 0, RP, 3 * mm, fill=1, stroke=0)

    # QR code
    qr_bytes = generate_qr_image(ticket.qr_token, size=5)
    qsz = 20 * mm
    qx  = rx + (RP - qsz) / 2
    qy  = H / 2 - qsz / 2 + 3 * mm

    c.setFillColor(WHITE)
    c.roundRect(qx - 1.5*mm, qy - 1.5*mm, qsz + 3*mm, qsz + 3*mm, 1*mm, fill=1, stroke=0)
    c.drawImage(ImageReader(io.BytesIO(qr_bytes)), qx, qy, qsz, qsz)

    c.setFillColor(ACCENTL)
    c.setFont('Helvetica-Bold', 4.5)
    c.drawCentredString(rx + RP / 2, qy - 3.5 * mm, 'SCAN TO VERIFY')

    # Price on right panel
    c.setFillColor(BADGEBG)
    c.roundRect(rx + 2 * mm, 8.5 * mm, RP - 4 * mm, 5 * mm, 1.5 * mm, fill=1, stroke=0)
    c.setFillColor(ACCENTL)
    c.setFont('Helvetica-Bold', 5.5)
    c.drawCentredString(rx + RP / 2, 9.8 * mm, theme['price'])

    # ── Perforated dividers ──────────────────────────────────────────
    c.saveState()
    c.setStrokeColor(colors.HexColor('#cccccc'))
    c.setLineWidth(0.4)
    c.setDash(2, 3)
    c.line(LP, 3 * mm, LP, H - 3 * mm)
    c.line(rx, 3 * mm, rx, H - 3 * mm)
    c.restoreState()

    # Notch semicircles
    for nx in [LP, rx]:
        c.setFillColor(CREAM)
        c.circle(nx, H - 3 * mm, 2.5 * mm, fill=1, stroke=0)
        c.circle(nx, 3 * mm,     2.5 * mm, fill=1, stroke=0)

    # ════════════════════════════════════════════════════════════════
    # CENTRE PANEL
    # ════════════════════════════════════════════════════════════════
    mx = LP

    # Faint watermark
    if os.path.exists(logo_path):
        wsz = 38 * mm
        wx  = mx + (MP - wsz) / 2
        wy  = (H - wsz) / 2
        c.saveState()
        c.setFillAlpha(0.05)
        c.drawImage(ImageReader(logo_path), wx, wy, wsz, wsz,
                    preserveAspectRatio=True, mask='auto')
        c.restoreState()

    # Accent bars on centre
    c.setFillColor(ACCENT)
    c.rect(mx, H - 3 * mm, MP, 3 * mm, fill=1, stroke=0)
    c.rect(mx, 0, MP, 3 * mm, fill=1, stroke=0)

    # ── Header ───────────────────────────────────────────────────────
    ht = H - 3 * mm - 4.5 * mm

    c.setFillColor(GREY)
    c.setFont('Helvetica', 5)
    c.drawCentredString(mx + MP / 2, ht, 'PANDORA AWARDS  ·  8TH EDITION  ·  ABUJA 2026')

    c.setFillColor(BLACK)
    c.setFont('Helvetica-Bold', 9)
    c.drawCentredString(mx + MP / 2, ht - 5.5 * mm, 'PANDORA AWARD 8TH EDITION E-TICKET')

    # Accent divider
    c.setStrokeColor(ACCENT)
    c.setLineWidth(0.7)
    c.line(mx + 4*mm, ht - 7*mm, mx + MP - 4*mm, ht - 7*mm)

    # ── Guest name ───────────────────────────────────────────────────
    gname = ticket.guest.full_name.upper()
    fname_size = 9 if len(gname) <= 22 else 7.5
    c.setFillColor(BLACK)
    c.setFont('Helvetica-Bold', fname_size)
    c.drawCentredString(mx + MP / 2, ht - 11.5 * mm, gname[:32])

    # Ticket type pill — accent coloured
    ttype_label = theme['label']
    pill_w = max(len(ttype_label) * 3.2 + 10, 22) * mm / 10
    pill_x = mx + MP / 2 - pill_w / 2
    pill_y = ht - 16.5 * mm
    c.setFillColor(colors.HexColor(theme['panel']))
    c.roundRect(pill_x, pill_y, pill_w, 4.5 * mm, 2 * mm, fill=1, stroke=0)
    c.setStrokeColor(ACCENT)
    c.setLineWidth(0.5)
    c.roundRect(pill_x, pill_y, pill_w, 4.5 * mm, 2 * mm, fill=0, stroke=1)
    c.setFillColor(ACCENT)
    c.setFont('Helvetica-Bold', 5.5)
    c.drawCentredString(mx + MP / 2, pill_y + 1.3 * mm, ttype_label)

    # ── Two-column info grid ──────────────────────────────────────────
    c1x = mx + 4 * mm
    c2x = mx + MP / 2 + 2 * mm
    gy  = ht - 23 * mm
    gap = 8 * mm

    def cell(x, y, label, val, chars=22):
        c.setFillColor(ACCENT)
        c.setFont('Helvetica-Bold', 4.5)
        c.drawString(x, y, label)
        c.setFillColor(BLACK)
        c.setFont('Helvetica', 6)
        c.drawString(x, y - 3.5 * mm, str(val)[:chars])

    cell(c1x, gy,         'FULL NAME',  ticket.guest.full_name)
    cell(c2x, gy,         'EVENT DATE', ticket.event.event_date.strftime('%A, %d %B %Y'))
    cell(c1x, gy - gap,   'PHONE',      ticket.guest.phone_number)
    cell(c2x, gy - gap,   'TIME',       'Red Carpet 4PM  ·  Main Event 6PM')
    cell(c1x, gy - gap*2, 'TICKET NO.', ticket.ticket_number, chars=18)
    cell(c2x, gy - gap*2, 'VENUE',      'A Class Event Center, Sapphire Hall', chars=28)

    # ── Footer ───────────────────────────────────────────────────────
    c.setStrokeColor(ACCENT)
    c.setLineWidth(0.3)
    c.line(mx + 4*mm, 5.5*mm, mx + MP - 4*mm, 5.5*mm)
    c.setFillColor(LGREY)
    c.setFont('Helvetica-Oblique', 4.5)
    c.drawCentredString(mx + MP / 2, 4 * mm,
        'Non-transferable. Present at entrance for verification.')

    c.save()
    return buf.getvalue()


def _draw_photo_placeholder(c, x, y, w, h):
    from reportlab.lib import colors
    c.setFillColor(colors.HexColor('#1a3a20'))
    c.rect(x, y, w, h, fill=1, stroke=0)
    c.setFillColor(colors.HexColor('#c9960c'))
    c.setFont('Helvetica', 7)
    c.drawCentredString(x + w / 2, y + h / 2, 'PHOTO')

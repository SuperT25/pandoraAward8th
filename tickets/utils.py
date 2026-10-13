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
# Photo loader
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
# Ticket colour themes — matching the reference designs exactly
# ---------------------------------------------------------------------------

TICKET_THEMES = {
    'REGULAR': {
        'bg':          '#1a1008',   # Very dark brown-black
        'accent':      '#c9960c',   # Gold
        'accent2':     '#e8c84a',
        'box_bg':      '#2a1e0a',
        'box_border':  '#c9960c',
        'stub_bg':     '#1a1008',
        'stub_accent': '#c9960c',
        'text_main':   '#ffffff',
        'text_sub':    '#c9960c',
        'text_body':   '#e0d0b0',
        'price':       '₦30,000',
        'label':       'REGULAR',
        'watermark':   '#c9960c',
    },
    'VIP': {
        'bg':          '#0a1428',   # Dark navy blue
        'accent':      '#4ab0ff',   # Blue
        'accent2':     '#80ccff',
        'box_bg':      '#0f1e3a',
        'box_border':  '#4ab0ff',
        'stub_bg':     '#0a1428',
        'stub_accent': '#4ab0ff',
        'text_main':   '#ffffff',
        'text_sub':    '#4ab0ff',
        'text_body':   '#b0d0f0',
        'price':       '₦100,000',
        'label':       'VIP',
        'watermark':   '#4ab0ff',
    },
    'SPECIAL GUEST SEAT': {
        'bg':          '#2a0a1a',   # Dark maroon
        'accent':      '#e080a0',   # Pink
        'accent2':     '#f0b0c0',
        'box_bg':      '#3a1028',
        'box_border':  '#e080a0',
        'stub_bg':     '#2a0a1a',
        'stub_accent': '#e080a0',
        'text_main':   '#ffffff',
        'text_sub':    '#e080a0',
        'text_body':   '#f0c0d0',
        'price':       '₦300,000',
        'label':       'SPECIAL GUEST SEAT',
        'watermark':   '#e080a0',
    },
    'SPECIAL GUEST': {
        'bg':          '#2a0a1a',
        'accent':      '#e080a0',
        'accent2':     '#f0b0c0',
        'box_bg':      '#3a1028',
        'box_border':  '#e080a0',
        'stub_bg':     '#2a0a1a',
        'stub_accent': '#e080a0',
        'text_main':   '#ffffff',
        'text_sub':    '#e080a0',
        'text_body':   '#f0c0d0',
        'price':       '₦300,000',
        'label':       'SPECIAL GUEST',
        'watermark':   '#e080a0',
    },
    'GOLD TABLE': {
        'bg':          '#1e1004',   # Rich dark brown
        'accent':      '#c9960c',   # Gold
        'accent2':     '#e8c84a',
        'box_bg':      '#2e1a08',
        'box_border':  '#c9960c',
        'stub_bg':     '#1e1004',
        'stub_accent': '#c9960c',
        'text_main':   '#ffffff',
        'text_sub':    '#c9960c',
        'text_body':   '#e0d0b0',
        'price':       '₦800,000',
        'label':       'GOLD TABLE',
        'watermark':   '#c9960c',
    },
    'MEDIA': {
        'bg':          '#0a1428',
        'accent':      '#4ab0ff',
        'accent2':     '#80ccff',
        'box_bg':      '#0f1e3a',
        'box_border':  '#4ab0ff',
        'stub_bg':     '#0a1428',
        'stub_accent': '#4ab0ff',
        'text_main':   '#ffffff',
        'text_sub':    '#4ab0ff',
        'text_body':   '#b0d0f0',
        'price':       'PRESS',
        'label':       'MEDIA',
        'watermark':   '#4ab0ff',
    },
    'STAFF': {
        'bg':          '#111111',
        'accent':      '#888888',
        'accent2':     '#bbbbbb',
        'box_bg':      '#222222',
        'box_border':  '#888888',
        'stub_bg':     '#111111',
        'stub_accent': '#888888',
        'text_main':   '#ffffff',
        'text_sub':    '#aaaaaa',
        'text_body':   '#cccccc',
        'price':       'CREW',
        'label':       'STAFF',
        'watermark':   '#888888',
    },
}

DEFAULT_THEME = TICKET_THEMES['REGULAR']


def get_theme(name: str) -> dict:
    return TICKET_THEMES.get(name.upper(), DEFAULT_THEME)


# ---------------------------------------------------------------------------
# PDF Ticket — matches reference designs exactly
# Size: 210 x 99 mm  (landscape boarding-pass)
# Layout: Left main panel (~155mm) | Perforated divider | Right stub (~55mm)
# ---------------------------------------------------------------------------

def generate_ticket_pdf(ticket) -> bytes:
    from reportlab.lib.units import mm
    from reportlab.lib import colors
    from reportlab.lib.utils import ImageReader
    from reportlab.pdfgen import canvas

    W = 210 * mm
    H = 99  * mm
    STUB = 55 * mm   # right stub width
    MAIN = W - STUB  # left main panel width

    theme = get_theme(ticket.ticket_type.name)

    BG        = colors.HexColor(theme['bg'])
    ACCENT    = colors.HexColor(theme['accent'])
    ACCENT2   = colors.HexColor(theme['accent2'])
    BOX_BG    = colors.HexColor(theme['box_bg'])
    BOX_BDR   = colors.HexColor(theme['box_border'])
    STUB_BG   = colors.HexColor(theme['stub_bg'])
    STUB_ACC  = colors.HexColor(theme['stub_accent'])
    TEXT_MAIN = colors.HexColor(theme['text_main'])
    TEXT_SUB  = colors.HexColor(theme['text_sub'])
    TEXT_BODY = colors.HexColor(theme['text_body'])
    WM_COLOR  = colors.HexColor(theme['watermark'])
    WHITE     = colors.white

    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=(W, H))

    # ════════════════════════════════════════════════════════════════
    # MAIN PANEL (left)
    # ════════════════════════════════════════════════════════════════
    c.setFillColor(BG)
    c.roundRect(0, 0, MAIN, H, 4 * mm, fill=1, stroke=0)

    # Top accent bar
    c.setFillColor(ACCENT)
    c.rect(0, H - 2.5 * mm, MAIN, 2.5 * mm, fill=1, stroke=0)

    # Bottom accent bar
    c.rect(0, 0, MAIN, 2.5 * mm, fill=1, stroke=0)

    # Bottom-right triangle accent (like in reference)
    p = c.beginPath()
    p.moveTo(MAIN - 18 * mm, 0)
    p.lineTo(MAIN, 0)
    p.lineTo(MAIN, 18 * mm)
    p.close()
    c.setFillColor(ACCENT)
    c.drawPath(p, fill=1, stroke=0)

    # ── Logo + Title ─────────────────────────────────────────────────
    logo_path = os.path.join(settings.BASE_DIR, 'static', 'img', 'pandora-logo.jpeg')
    logo_size = 16 * mm
    logo_x, logo_y = 5 * mm, H - 2.5 * mm - logo_size - 2 * mm

    if os.path.exists(logo_path):
        c.drawImage(ImageReader(logo_path), logo_x, logo_y, logo_size, logo_size,
                    preserveAspectRatio=True, mask='auto')

    title_x = logo_x + logo_size + 3 * mm
    title_y = H - 2.5 * mm - 9 * mm
    c.setFillColor(TEXT_MAIN)
    c.setFont('Helvetica-Bold', 16)
    c.drawString(title_x, title_y, 'PANDORA AWARDS')

    c.setFillColor(TEXT_SUB)
    c.setFont('Helvetica', 7.5)
    c.drawString(title_x, title_y - 5.5 * mm, '8TH EDITION  •  LIVE IN ABUJA')

    # Accent divider under header
    c.setStrokeColor(ACCENT)
    c.setLineWidth(0.5)
    c.line(5 * mm, H - 2.5 * mm - 22 * mm, MAIN - 5 * mm, H - 2.5 * mm - 22 * mm)

    # ── Ticket Type + Price box ──────────────────────────────────────
    box_y = H - 2.5 * mm - 36 * mm
    box_h = 12 * mm
    box_x = 5 * mm
    box_w = MAIN - 10 * mm

    c.setFillColor(BOX_BG)
    c.roundRect(box_x, box_y, box_w, box_h, 2 * mm, fill=1, stroke=0)
    c.setStrokeColor(BOX_BDR)
    c.setLineWidth(0.8)
    c.roundRect(box_x, box_y, box_w, box_h, 2 * mm, fill=0, stroke=1)

    # TICKET TYPE label + value
    c.setFillColor(TEXT_SUB)
    c.setFont('Helvetica', 5.5)
    c.drawString(box_x + 4 * mm, box_y + box_h - 4 * mm, 'TICKET TYPE')

    c.setFillColor(TEXT_MAIN)
    c.setFont('Helvetica-Bold', 10)
    c.drawString(box_x + 4 * mm, box_y + 2.5 * mm, theme['label'])

    # Vertical divider in box
    mid_box = box_x + box_w * 0.5
    c.setStrokeColor(BOX_BDR)
    c.setLineWidth(0.4)
    c.line(mid_box, box_y + 2 * mm, mid_box, box_y + box_h - 2 * mm)

    # PRICE label + value
    c.setFillColor(TEXT_SUB)
    c.setFont('Helvetica', 5.5)
    c.drawString(mid_box + 4 * mm, box_y + box_h - 4 * mm, 'PRICE')

    c.setFillColor(ACCENT)
    c.setFont('Helvetica-Bold', 11)
    c.drawString(mid_box + 4 * mm, box_y + 2.5 * mm, theme['price'])

    # ── Date / Time / Venue ──────────────────────────────────────────
    info_y = box_y - 6 * mm

    c.setFillColor(TEXT_MAIN)
    c.setFont('Helvetica-Bold', 9)
    date_str = ticket.event.event_date.strftime('SUNDAY, %d %B %Y').upper()
    c.drawString(5 * mm, info_y, date_str)

    c.setFillColor(TEXT_SUB)
    c.setFont('Helvetica-Bold', 7.5)
    c.drawString(5 * mm, info_y - 5.5 * mm, 'RED CARPET 4PM  •  MAIN EVENT 6PM')

    c.setFillColor(TEXT_MAIN)
    c.setFont('Helvetica-Bold', 7.5)
    c.drawString(5 * mm, info_y - 11 * mm, 'A CLASS EVENT CENTER  •  SAPPHIRE HALL')

    c.setFillColor(TEXT_BODY)
    c.setFont('Helvetica', 6.5)
    c.drawString(5 * mm, info_y - 16 * mm, 'Maitama, Abuja FCT, Nigeria')

    # ── Guest Name field ─────────────────────────────────────────────
    name_y = info_y - 27 * mm
    name_box_w = MAIN - 10 * mm

    c.setFillColor(BOX_BG)
    c.roundRect(5 * mm, name_y - 1 * mm, name_box_w, 10 * mm, 1.5 * mm, fill=1, stroke=0)
    c.setStrokeColor(BOX_BDR)
    c.setLineWidth(0.5)
    c.roundRect(5 * mm, name_y - 1 * mm, name_box_w, 10 * mm, 1.5 * mm, fill=0, stroke=1)

    c.setFillColor(TEXT_SUB)
    c.setFont('Helvetica-Bold', 5.5)
    c.drawString(8 * mm, name_y + 7 * mm, 'NAME')

    # Guest name value
    c.setFillColor(TEXT_MAIN)
    c.setFont('Helvetica-Bold', 9)
    gname = ticket.guest.full_name.upper()
    c.drawString(8 * mm, name_y + 1.5 * mm, gname[:35])

    # Underline under name
    c.setStrokeColor(ACCENT)
    c.setLineWidth(0.4)
    c.line(8 * mm, name_y + 1 * mm, 5 * mm + name_box_w - 3 * mm, name_y + 1 * mm)

    # ── Watermark "PANDORA AWARD" text ───────────────────────────────
    c.saveState()
    c.setFillColor(WM_COLOR)
    c.setFillAlpha(0.06)
    c.setFont('Helvetica-Bold', 28)
    c.translate(MAIN / 2, H / 2 - 5 * mm)
    c.rotate(0)
    c.drawCentredString(0, 0, 'PANDORA AWARD')
    c.restoreState()

    # ── ONE TICKET • ONE ENTRY ───────────────────────────────────────
    c.setFillColor(TEXT_SUB)
    c.setFont('Helvetica-Bold', 6)
    c.drawString(5 * mm, 4 * mm, 'ONE TICKET  •  ONE ENTRY')

    # ════════════════════════════════════════════════════════════════
    # PERFORATED DIVIDER
    # ════════════════════════════════════════════════════════════════
    c.saveState()
    c.setStrokeColor(ACCENT)
    c.setLineWidth(0.6)
    c.setDash(3, 4)
    c.line(MAIN, 4 * mm, MAIN, H - 4 * mm)
    c.restoreState()

    # Semicircle notches
    c.setFillColor(BG)
    c.circle(MAIN, H - 4 * mm, 3 * mm, fill=1, stroke=0)
    c.circle(MAIN, 4 * mm, 3 * mm, fill=1, stroke=0)

    # ════════════════════════════════════════════════════════════════
    # RIGHT STUB
    # ════════════════════════════════════════════════════════════════
    stub_x = MAIN
    c.setFillColor(STUB_BG)
    c.roundRect(stub_x, 0, STUB, H, 4 * mm, fill=1, stroke=0)

    # Stub top accent bar
    c.setFillColor(STUB_ACC)
    c.rect(stub_x, H - 2.5 * mm, STUB, 2.5 * mm, fill=1, stroke=0)

    # Stub bottom accent bar
    c.rect(stub_x, 0, STUB, 2.5 * mm, fill=1, stroke=0)

    # Bottom-left triangle on stub
    p2 = c.beginPath()
    p2.moveTo(stub_x, 0)
    p2.lineTo(stub_x + 16 * mm, 0)
    p2.lineTo(stub_x, 16 * mm)
    p2.close()
    c.setFillColor(STUB_ACC)
    c.drawPath(p2, fill=1, stroke=0)

    # ── QR Code ──────────────────────────────────────────────────────
    qr_bytes = generate_qr_image(ticket.qr_token, size=6)
    qr_size = 34 * mm
    qr_x = stub_x + (STUB - qr_size) / 2
    qr_y = H / 2 - qr_size / 2 + 4 * mm

    # White background for QR
    c.setFillColor(WHITE)
    c.roundRect(qr_x - 2 * mm, qr_y - 2 * mm, qr_size + 4 * mm, qr_size + 4 * mm,
                1.5 * mm, fill=1, stroke=0)
    c.setStrokeColor(STUB_ACC)
    c.setLineWidth(1)
    c.roundRect(qr_x - 2 * mm, qr_y - 2 * mm, qr_size + 4 * mm, qr_size + 4 * mm,
                1.5 * mm, fill=0, stroke=1)
    c.drawImage(ImageReader(io.BytesIO(qr_bytes)), qr_x, qr_y, qr_size, qr_size)

    # ── SCAN AT ENTRY ────────────────────────────────────────────────
    scan_y = qr_y - 5 * mm
    c.setFillColor(TEXT_MAIN)
    c.setFont('Helvetica-Bold', 7)
    c.drawString(stub_x + 3 * mm, scan_y, 'SCAN AT ENTRY')

    # Ticket number
    c.setFillColor(TEXT_SUB)
    c.setFont('Helvetica', 6)
    c.drawString(stub_x + 3 * mm, scan_y - 4.5 * mm, ticket.ticket_number)

    # KEEP THIS TICKET
    keep_y = scan_y - 11 * mm
    c.setFillColor(TEXT_MAIN)
    c.setFont('Helvetica-Bold', 6.5)
    c.drawString(stub_x + 3 * mm, keep_y, 'KEEP THIS')
    c.drawString(stub_x + 3 * mm, keep_y - 4.5 * mm, 'TICKET')

    c.save()
    return buf.getvalue()


def _draw_photo_placeholder(c, x, y, w, h):
    from reportlab.lib import colors as _colors
    c.setFillColor(_colors.HexColor('#1a1008'))
    c.rect(x, y, w, h, fill=1, stroke=0)
    c.setFillColor(_colors.HexColor('#c9960c'))
    c.setFont('Helvetica', 7)
    c.drawCentredString(x + w / 2, y + h / 2, 'PHOTO')

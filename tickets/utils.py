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
# Photo loader — works with Cloudinary and local
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
# Ticket colour themes
# ---------------------------------------------------------------------------

TICKET_THEMES = {
    'REGULAR': {
        'header_bg':   '#0a0a2e',   # Deep dark blue
        'header_acc':  '#c9960c',   # Gold
        'accent':      '#c9960c',
        'accent2':     '#e8c84a',
        'grid_bg':     '#ffffff',
        'grid_label':  '#c9960c',
        'grid_value':  '#111111',
        'stub_bg':     '#f0f4ff',
        'stub_badge':  '#0a0a2e',
        'stub_text':   '#0a0a2e',
        'footer_bg':   '#0a0a2e',
        'footer_text': '#c9960c',
        'price':       '₦30,000',
        'label':       'REGULAR',
    },
    'VIP': {
        'header_bg':   '#001a3a',
        'header_acc':  '#4ab0ff',
        'accent':      '#4ab0ff',
        'accent2':     '#80ccff',
        'grid_bg':     '#ffffff',
        'grid_label':  '#0050aa',
        'grid_value':  '#111111',
        'stub_bg':     '#f0f8ff',
        'stub_badge':  '#001a3a',
        'stub_text':   '#001a3a',
        'footer_bg':   '#001a3a',
        'footer_text': '#4ab0ff',
        'price':       '₦100,000',
        'label':       'VIP',
    },
    'SPECIAL GUEST SEAT': {
        'header_bg':   '#1a0028',
        'header_acc':  '#d080ff',
        'accent':      '#d080ff',
        'accent2':     '#e8b0ff',
        'grid_bg':     '#ffffff',
        'grid_label':  '#8800cc',
        'grid_value':  '#111111',
        'stub_bg':     '#faf0ff',
        'stub_badge':  '#1a0028',
        'stub_text':   '#1a0028',
        'footer_bg':   '#1a0028',
        'footer_text': '#d080ff',
        'price':       '₦300,000',
        'label':       'SPECIAL GUEST SEAT',
    },
    'SPECIAL GUEST': {
        'header_bg':   '#1a0028',
        'header_acc':  '#d080ff',
        'accent':      '#d080ff',
        'accent2':     '#e8b0ff',
        'grid_bg':     '#ffffff',
        'grid_label':  '#8800cc',
        'grid_value':  '#111111',
        'stub_bg':     '#faf0ff',
        'stub_badge':  '#1a0028',
        'stub_text':   '#1a0028',
        'footer_bg':   '#1a0028',
        'footer_text': '#d080ff',
        'price':       '₦300,000',
        'label':       'SPECIAL GUEST',
    },
    'GOLD TABLE': {
        'header_bg':   '#1a0e00',
        'header_acc':  '#c9960c',
        'accent':      '#c9960c',
        'accent2':     '#e8c84a',
        'grid_bg':     '#ffffff',
        'grid_label':  '#8a6400',
        'grid_value':  '#111111',
        'stub_bg':     '#fffaf0',
        'stub_badge':  '#1a0e00',
        'stub_text':   '#1a0e00',
        'footer_bg':   '#1a0e00',
        'footer_text': '#c9960c',
        'price':       '₦800,000',
        'label':       'GOLD TABLE',
    },
    'MEDIA': {
        'header_bg':   '#001428',
        'header_acc':  '#00aaff',
        'accent':      '#00aaff',
        'accent2':     '#80d4ff',
        'grid_bg':     '#ffffff',
        'grid_label':  '#006699',
        'grid_value':  '#111111',
        'stub_bg':     '#f0faff',
        'stub_badge':  '#001428',
        'stub_text':   '#001428',
        'footer_bg':   '#001428',
        'footer_text': '#00aaff',
        'price':       'PRESS',
        'label':       'MEDIA',
    },
    'STAFF': {
        'header_bg':   '#111111',
        'header_acc':  '#888888',
        'accent':      '#888888',
        'accent2':     '#bbbbbb',
        'grid_bg':     '#ffffff',
        'grid_label':  '#555555',
        'grid_value':  '#111111',
        'stub_bg':     '#f5f5f5',
        'stub_badge':  '#111111',
        'stub_text':   '#111111',
        'footer_bg':   '#111111',
        'footer_text': '#888888',
        'price':       'CREW',
        'label':       'STAFF',
    },
}

DEFAULT_THEME = TICKET_THEMES['REGULAR']


def get_theme(name: str) -> dict:
    return TICKET_THEMES.get(name.upper(), DEFAULT_THEME)


# ---------------------------------------------------------------------------
# Barcode (Code128 style — simple lines)
# ---------------------------------------------------------------------------

def _draw_barcode(c, x, y, width, height, text):
    """Draw a simple visual barcode (decorative) under the ticket number."""
    from reportlab.lib import colors as _colors
    import hashlib
    # Generate deterministic bar pattern from ticket number
    h = hashlib.md5(text.encode()).hexdigest()
    bars = []
    for ch in h:
        v = int(ch, 16)
        bars.append(v)

    bar_count = 60
    bar_w = width / (bar_count * 1.5)
    cx = x
    for i in range(bar_count):
        v = bars[i % len(bars)]
        bw = bar_w * (1 + (v % 3) * 0.4)
        if v % 2 == 0:
            c.setFillColor(_colors.black)
            c.rect(cx, y, bw, height, fill=1, stroke=0)
        cx += bw + bar_w * 0.5


# ---------------------------------------------------------------------------
# PDF Ticket — matches EventHub-style reference with Pandora branding
# Size: A5 landscape = 210 x 148 mm
# Layout: Main panel (left ~155mm) | Right stub (~55mm)
# ---------------------------------------------------------------------------

def generate_ticket_pdf(ticket) -> bytes:
    from reportlab.lib.pagesizes import A5, landscape
    from reportlab.lib.units import mm
    from reportlab.lib import colors
    from reportlab.lib.utils import ImageReader
    from reportlab.pdfgen import canvas

    PAGE_W, PAGE_H = landscape(A5)   # 210 x 148 mm
    STUB_W = 58 * mm
    MAIN_W = PAGE_W - STUB_W

    theme = get_theme(ticket.ticket_type.name)

    HDR_BG    = colors.HexColor(theme['header_bg'])
    HDR_ACC   = colors.HexColor(theme['header_acc'])
    ACCENT    = colors.HexColor(theme['accent'])
    ACCENT2   = colors.HexColor(theme['accent2'])
    GRID_BG   = colors.HexColor(theme['grid_bg'])
    GL        = colors.HexColor(theme['grid_label'])
    GV        = colors.HexColor(theme['grid_value'])
    STUB_BG   = colors.HexColor(theme['stub_bg'])
    STUB_B    = colors.HexColor(theme['stub_badge'])
    STUB_T    = colors.HexColor(theme['stub_text'])
    FTR_BG    = colors.HexColor(theme['footer_bg'])
    FTR_TXT   = colors.HexColor(theme['footer_text'])
    WHITE     = colors.white
    BLACK     = colors.black
    GREY      = colors.HexColor('#666666')
    LGREY     = colors.HexColor('#999999')

    HEADER_H  = 58 * mm   # top header band height
    FOOTER_H  = 10 * mm   # bottom footer band height
    GRID_H    = PAGE_H - HEADER_H - FOOTER_H  # middle grid area

    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=(PAGE_W, PAGE_H))

    # ════════════════════════════════════════════════════════════════════
    # MAIN PANEL
    # ════════════════════════════════════════════════════════════════════

    # ── HEADER BAND ──────────────────────────────────────────────────────
    header_y = PAGE_H - HEADER_H
    c.setFillColor(HDR_BG)
    c.rect(0, header_y, MAIN_W, HEADER_H, fill=1, stroke=0)

    # Background image on header (pa-logo.jpeg used as watermark bg)
    bg_path = os.path.join(settings.BASE_DIR, 'static', 'img', 'pa-logo.jpeg')
    if os.path.exists(bg_path):
        c.saveState()
        c.setFillAlpha(0.3)
        c.drawImage(ImageReader(bg_path), 0, header_y, MAIN_W, HEADER_H,
                    preserveAspectRatio=False, mask='auto')
        c.restoreState()
        # Re-draw dark overlay
        c.setFillColor(HDR_BG)
        c.saveState()
        c.setFillAlpha(0.55)
        c.rect(0, header_y, MAIN_W, HEADER_H, fill=1, stroke=0)
        c.restoreState()

    # ── Logo top-left ─────────────────────────────────────────────────
    # Try new PA logo first, fall back to old logo
    logo_paths = [
        os.path.join(settings.BASE_DIR, 'static', 'img', 'pa-logo.jpeg'),
        os.path.join(settings.BASE_DIR, 'static', 'img', 'pa-logo.png'),
        os.path.join(settings.BASE_DIR, 'static', 'img', 'pandora-logo.jpeg'),
    ]
    logo_path = None
    for p in logo_paths:
        if os.path.exists(p):
            logo_path = p
            break

    if logo_path:
        logo_sz = 18 * mm
        c.drawImage(ImageReader(logo_path), 5 * mm, PAGE_H - 5 * mm - logo_sz,
                    logo_sz, logo_sz, preserveAspectRatio=True, mask='auto')

    # ── "PANDORA AWARDS" title ────────────────────────────────────────
    title_x = 27 * mm
    title_y = PAGE_H - 10 * mm
    c.setFillColor(WHITE)
    c.setFont('Helvetica-Bold', 11)
    c.drawString(title_x, title_y, 'PANDORA AWARDS')
    c.setFillColor(ACCENT2)
    c.setFont('Helvetica', 7)
    c.drawString(title_x, title_y - 4.5 * mm, 'Events Made Memorable')

    # Vertical separator
    c.setStrokeColor(ACCENT)
    c.setLineWidth(1)
    c.line(title_x + 62 * mm, PAGE_H - 5 * mm, title_x + 62 * mm, PAGE_H - 22 * mm)

    # ── Date block (top-right of header) ─────────────────────────────
    date_x = title_x + 66 * mm
    c.setFillColor(LGREY)
    c.setFont('Helvetica', 7)
    c.drawString(date_x, PAGE_H - 10 * mm,
                 ticket.event.event_date.strftime('%a').upper())
    c.setFillColor(WHITE)
    c.setFont('Helvetica-Bold', 22)
    c.drawString(date_x, PAGE_H - 20 * mm,
                 ticket.event.event_date.strftime('%d'))
    c.setFillColor(ACCENT2)
    c.setFont('Helvetica-Bold', 9)
    c.drawString(date_x, PAGE_H - 25 * mm,
                 ticket.event.event_date.strftime('%b %Y').upper())

    # ── "PANDORA AWARDS 8TH EDITION" big text ────────────────────────
    big_y = PAGE_H - HEADER_H + 32 * mm
    c.setFillColor(ACCENT)
    c.setFont('Helvetica-Bold', 7)
    c.drawString(5 * mm, big_y + 6 * mm, 'CELEBRATING EXCELLENCE')
    c.setFillColor(WHITE)
    c.setFont('Helvetica-Bold', 20)
    c.drawString(5 * mm, big_y - 3 * mm, 'PANDORA AWARDS')
    c.setFillColor(ACCENT2)
    c.setFont('Helvetica-Bold', 14)
    c.drawString(5 * mm, big_y - 11 * mm, '8th Edition')

    # Venue + time on header right side
    venue_x = 90 * mm
    venue_y = big_y - 3 * mm
    c.setFillColor(LGREY)
    c.setFont('Helvetica', 6.5)
    c.drawString(venue_x, venue_y + 2 * mm, '📍  A Class Event Center, Sapphire Hall')
    c.drawString(venue_x, venue_y - 2.5 * mm, '     Maitama, Abuja FCT, Nigeria')
    c.drawString(venue_x, venue_y - 7 * mm, '🕐  Red Carpet 4PM  •  Main Event 6PM')

    # Ticket type badge on header
    badge_y = PAGE_H - HEADER_H + 6 * mm
    badge_w = 40 * mm
    c.setFillColor(ACCENT)
    c.roundRect(5 * mm, badge_y, badge_w, 6 * mm, 1.5 * mm, fill=1, stroke=0)
    c.setFillColor(HDR_BG)
    c.setFont('Helvetica-Bold', 7.5)
    c.drawCentredString(5 * mm + badge_w / 2, badge_y + 1.8 * mm,
                        theme['label'] + '  •  ' + theme['price'])

    # ── GRID AREA (white) ─────────────────────────────────────────────
    grid_y = FOOTER_H
    c.setFillColor(GRID_BG)
    c.rect(0, grid_y, MAIN_W, GRID_H, fill=1, stroke=0)

    # Grid lines
    c.setStrokeColor(colors.HexColor('#dddddd'))
    c.setLineWidth(0.4)

    # Vertical dividers for grid
    col_w = MAIN_W / 3
    for i in [1, 2]:
        c.line(col_w * i, grid_y + 2 * mm, col_w * i, grid_y + GRID_H - 2 * mm)

    # Horizontal divider
    mid_grid_y = grid_y + GRID_H / 2
    c.line(2 * mm, mid_grid_y, MAIN_W - 2 * mm, mid_grid_y)

    def grid_cell(x, y, w, h, label, value, value2=None):
        pad = 3 * mm
        c.setFillColor(GL)
        c.setFont('Helvetica-Bold', 5.5)
        c.drawString(x + pad, y + h - 5 * mm, label)
        c.setFillColor(GV)
        c.setFont('Helvetica-Bold', 9)
        c.drawString(x + pad, y + h - 11 * mm, str(value)[:26])
        if value2:
            c.setFont('Helvetica', 7.5)
            c.setFillColor(GREY)
            c.drawString(x + pad, y + h - 15.5 * mm, str(value2)[:28])

    row1_y = mid_grid_y
    row1_h = GRID_H / 2
    row2_y = grid_y
    row2_h = GRID_H / 2

    # Row 1: Ticket Holder | Ticket Type | Price
    grid_cell(0,       row1_y, col_w,   row1_h, 'TICKET HOLDER', ticket.guest.full_name)
    grid_cell(col_w,   row1_y, col_w,   row1_h, 'TICKET TYPE',   ticket.ticket_type.name)
    grid_cell(col_w*2, row1_y, col_w,   row1_h, 'PRICE',         theme['price'])

    # Row 2: Event | Venue | Date & Time
    grid_cell(0,       row2_y, col_w,   row2_h, 'EVENT',
              'Pandora Awards 8th Edition')
    grid_cell(col_w,   row2_y, col_w,   row2_h, 'VENUE',
              'A Class Event Center', 'Sapphire Hall, Maitama, Abuja')
    grid_cell(col_w*2, row2_y, col_w,   row2_h, 'DATE & TIME',
              ticket.event.event_date.strftime('%a, %d %b %Y'),
              'Red Carpet 4PM  •  Main Event 6PM')

    # ── Barcode + ticket number ───────────────────────────────────────
    bar_y = grid_y + 1 * mm
    bar_h = 6 * mm
    bar_w = MAIN_W * 0.55
    bar_x = 5 * mm
    _draw_barcode(c, bar_x, bar_y, bar_w, bar_h, ticket.ticket_number)
    c.setFillColor(BLACK)
    c.setFont('Helvetica', 7)
    c.drawString(bar_x, bar_y - 3.5 * mm, ticket.ticket_number)

    # ── Phone + Email row ─────────────────────────────────────────────
    phone_x = bar_x + bar_w + 5 * mm
    c.setFillColor(GL)
    c.setFont('Helvetica-Bold', 5.5)
    c.drawString(phone_x, bar_y + bar_h, 'PHONE')
    c.setFillColor(GV)
    c.setFont('Helvetica', 7.5)
    c.drawString(phone_x, bar_y + bar_h - 4.5 * mm, ticket.guest.phone_number)

    # ── FOOTER BAND ───────────────────────────────────────────────────
    c.setFillColor(FTR_BG)
    c.rect(0, 0, MAIN_W, FOOTER_H, fill=1, stroke=0)

    c.setFillColor(FTR_TXT)
    c.setFont('Helvetica-Bold', 7)
    c.drawCentredString(MAIN_W / 2, 3.5 * mm,
                        'THANK YOU FOR BEING PART OF PANDORA AWARDS 8TH EDITION')

    # ════════════════════════════════════════════════════════════════════
    # PERFORATED DIVIDER
    # ════════════════════════════════════════════════════════════════════
    div_x = MAIN_W
    c.saveState()
    c.setStrokeColor(GREY)
    c.setLineWidth(0.6)
    c.setDash(3, 4)
    c.line(div_x, 4 * mm, div_x, PAGE_H - 4 * mm)
    c.restoreState()

    # Notch circles
    c.setFillColor(colors.HexColor('#f0f0f0'))
    c.circle(div_x, PAGE_H - 4 * mm, 3 * mm, fill=1, stroke=0)
    c.circle(div_x, 4 * mm, 3 * mm, fill=1, stroke=0)

    # ════════════════════════════════════════════════════════════════════
    # RIGHT STUB
    # ════════════════════════════════════════════════════════════════════
    sx = MAIN_W

    c.setFillColor(STUB_BG)
    c.roundRect(sx, 0, STUB_W, PAGE_H, 3 * mm, fill=1, stroke=0)

    # ── "E-TICKET" badge ─────────────────────────────────────────────
    badge_stub_y = PAGE_H - 13 * mm
    badge_stub_w = STUB_W - 8 * mm
    badge_stub_x = sx + 4 * mm
    c.setFillColor(STUB_B)
    c.roundRect(badge_stub_x, badge_stub_y, badge_stub_w, 9 * mm, 2 * mm, fill=1, stroke=0)
    c.setFillColor(WHITE)
    c.setFont('Helvetica-Bold', 10)
    c.drawCentredString(badge_stub_x + badge_stub_w / 2, badge_stub_y + 2.5 * mm, 'E-TICKET')

    # ── "Scan to Enter" ───────────────────────────────────────────────
    c.setFillColor(STUB_T)
    c.setFont('Helvetica-Bold', 7.5)
    c.drawCentredString(sx + STUB_W / 2, PAGE_H - 18 * mm, 'Scan to Enter')

    # ── QR Code ───────────────────────────────────────────────────────
    qr_bytes = generate_qr_image(ticket.qr_token, size=6)
    qr_sz = 36 * mm
    qr_x = sx + (STUB_W - qr_sz) / 2
    qr_y = PAGE_H / 2 - qr_sz / 2 + 4 * mm

    c.setFillColor(WHITE)
    c.roundRect(qr_x - 1.5*mm, qr_y - 1.5*mm, qr_sz + 3*mm, qr_sz + 3*mm,
                2*mm, fill=1, stroke=0)
    c.setStrokeColor(ACCENT)
    c.setLineWidth(1)
    c.roundRect(qr_x - 1.5*mm, qr_y - 1.5*mm, qr_sz + 3*mm, qr_sz + 3*mm,
                2*mm, fill=0, stroke=1)
    c.drawImage(ImageReader(io.BytesIO(qr_bytes)), qr_x, qr_y, qr_sz, qr_sz)

    # ── Ticket ID ─────────────────────────────────────────────────────
    c.setFillColor(STUB_T)
    c.setFont('Helvetica', 6.5)
    c.drawCentredString(sx + STUB_W / 2, qr_y - 5 * mm, 'Ticket ID')
    c.setFont('Helvetica-Bold', 8.5)
    c.drawCentredString(sx + STUB_W / 2, qr_y - 9.5 * mm, ticket.ticket_number)

    # ── IMPORTANT instructions ────────────────────────────────────────
    imp_y = qr_y - 15 * mm
    c.setFillColor(ACCENT)
    c.setFont('Helvetica-Bold', 7)
    c.drawString(sx + 4 * mm, imp_y, 'IMPORTANT')

    instructions = [
        '1. Present QR code at entrance.',
        '2. Valid for one entry only.',
        '3. Keep this ticket safe.',
        '4. Non-transferable.',
    ]
    c.setFillColor(STUB_T)
    c.setFont('Helvetica', 6)
    for i, line in enumerate(instructions):
        c.drawString(sx + 4 * mm, imp_y - (i + 1) * 5 * mm, line)

    # ── "See You There!" footer ───────────────────────────────────────
    c.setFillColor(ACCENT)
    c.setFont('Helvetica-Oblique', 7.5)
    c.drawCentredString(sx + STUB_W / 2, 5 * mm, '✨ See You There!')

    c.save()
    return buf.getvalue()


def _draw_photo_placeholder(c, x, y, w, h):
    from reportlab.lib import colors as _colors
    c.setFillColor(_colors.HexColor('#eeeeee'))
    c.rect(x, y, w, h, fill=1, stroke=0)
    c.setFillColor(_colors.HexColor('#999999'))
    c.setFont('Helvetica', 7)
    c.drawCentredString(x + w / 2, y + h / 2, 'PHOTO')

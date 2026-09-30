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
        # Use the LAST value — Render's load balancer appends the real IP last.
        # The first value is client-controlled and can be forged.
        return x_forwarded.split(',')[-1].strip()
    return request.META.get('REMOTE_ADDR')


# ---------------------------------------------------------------------------
# QR Code generation
# ---------------------------------------------------------------------------

def generate_qr_image(qr_token: str, size: int = 10) -> bytes:
    """
    Generate a QR code PNG encoding the full live verify URL.
    No personal data in the QR — only the token.
    """
    verify_url = f"{SITE_URL}/verify/qr/{qr_token}/"    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=size,
        border=2,
    )
    qr.add_data(verify_url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="#0d2818", back_color="white")
    buffer = io.BytesIO()
    img.save(buffer, format='PNG')
    return buffer.getvalue()


def save_qr_to_file(ticket) -> str:
    """
    Save QR PNG via Django's default storage backend.
    Uses Cloudinary in production, local filesystem in development.
    """
    from django.core.files.base import ContentFile
    from django.core.files.storage import default_storage

    png_bytes = generate_qr_image(ticket.qr_token)
    rel_path = f"qrcodes/{ticket.ticket_number}.png"

    # Delete existing file to avoid duplicates on Cloudinary
    try:
        if default_storage.exists(rel_path):
            default_storage.delete(rel_path)
    except Exception:
        pass

    default_storage.save(rel_path, ContentFile(png_bytes))
    return rel_path


# ---------------------------------------------------------------------------
# Photo loading helper — works with local storage and Cloudinary
# ---------------------------------------------------------------------------

def _load_photo_reader(photo_field):
    """Return a ReportLab ImageReader for a Django ImageField, or None."""
    from reportlab.lib.utils import ImageReader
    if not photo_field:
        return None
    try:
        url = photo_field.url
        if url.startswith('http'):
            with urllib.request.urlopen(url) as resp:
                return ImageReader(io.BytesIO(resp.read()))
        else:
            return ImageReader(photo_field.path)
    except Exception:
        return None


# ---------------------------------------------------------------------------
# PDF Ticket generation
# Layout: Left dark green | Centre cream | Right dark green
# Size: 210 x 99 mm
# ---------------------------------------------------------------------------

def generate_ticket_pdf(ticket) -> bytes:
    """
    Generate the official Pandora Awards E-Ticket PDF.
    Returns PDF bytes.
    """
    from reportlab.lib.units import mm
    from reportlab.lib import colors
    from reportlab.lib.utils import ImageReader
    from reportlab.pdfgen import canvas

    # ── Page setup ──────────────────────────────────────────────────────────
    PAGE_W = 210 * mm
    PAGE_H = 99 * mm

    # Colour palette
    DARK_GREEN  = colors.HexColor('#0d2818')
    GOLD        = colors.HexColor('#c9960c')
    GOLD_LIGHT  = colors.HexColor('#e8c84a')
    CREAM       = colors.HexColor('#f5f0e8')
    WHITE       = colors.white
    DARK_TEXT   = colors.HexColor('#1a1a1a')
    GREY_TEXT   = colors.HexColor('#555555')

    # Panel widths
    LEFT_W  = 52 * mm
    RIGHT_W = 38 * mm
    MID_W   = PAGE_W - LEFT_W - RIGHT_W   # ~120 mm

    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=(PAGE_W, PAGE_H))

    # ════════════════════════════════════════════════════════════════════════
    # LEFT PANEL — dark green with logo
    # ════════════════════════════════════════════════════════════════════════
    c.setFillColor(DARK_GREEN)
    c.rect(0, 0, LEFT_W, PAGE_H, fill=1, stroke=0)

    # Gold top + bottom stripes
    c.setFillColor(GOLD)
    c.rect(0, PAGE_H - 4 * mm, LEFT_W, 4 * mm, fill=1, stroke=0)
    c.rect(0, 0, LEFT_W, 4 * mm, fill=1, stroke=0)

    # Gold diagonal accent
    c.setStrokeColor(GOLD)
    c.setLineWidth(1.5)
    c.line(0, PAGE_H - 4 * mm, LEFT_W * 0.6, 0)

    # Pandora logo
    logo_path = os.path.join(settings.BASE_DIR, 'static', 'img', 'pandora-logo.jpeg')
    if os.path.exists(logo_path):
        logo_size = 36 * mm
        logo_x = (LEFT_W - logo_size) / 2
        logo_y = PAGE_H / 2 - 2 * mm
        c.drawImage(
            ImageReader(logo_path),
            logo_x, logo_y, logo_size, logo_size,
            preserveAspectRatio=True, mask='auto',
        )
    else:
        c.setFillColor(GOLD)
        c.setFont('Helvetica-Bold', 11)
        c.drawCentredString(LEFT_W / 2, PAGE_H / 2 + 8 * mm, 'PANDORA')
        c.setFont('Helvetica-Bold', 9)
        c.drawCentredString(LEFT_W / 2, PAGE_H / 2 + 2 * mm, 'AWARDS')

    # "Celebrating Excellence"
    c.setFillColor(GOLD_LIGHT)
    c.setFont('Helvetica-Oblique', 6.5)
    c.drawCentredString(LEFT_W / 2, 8 * mm, 'Celebrating')
    c.drawCentredString(LEFT_W / 2, 5 * mm, 'Excellence')

    # ════════════════════════════════════════════════════════════════════════
    # RIGHT PANEL — dark green with QR code
    # ════════════════════════════════════════════════════════════════════════
    right_x = LEFT_W + MID_W
    c.setFillColor(DARK_GREEN)
    c.rect(right_x, 0, RIGHT_W, PAGE_H, fill=1, stroke=0)

    # Gold top + bottom stripes
    c.setFillColor(GOLD)
    c.rect(right_x, PAGE_H - 4 * mm, RIGHT_W, 4 * mm, fill=1, stroke=0)
    c.rect(right_x, 0, RIGHT_W, 4 * mm, fill=1, stroke=0)

    # Gold diagonal accent
    c.setStrokeColor(GOLD)
    c.setLineWidth(1.5)
    c.line(right_x + RIGHT_W * 0.4, PAGE_H - 4 * mm, right_x + RIGHT_W, 0)

    # QR code
    qr_bytes = generate_qr_image(ticket.qr_token, size=7)
    qr_size  = 26 * mm
    qr_x     = right_x + (RIGHT_W - qr_size) / 2
    qr_y     = PAGE_H / 2 + 2 * mm

    c.setFillColor(WHITE)
    c.roundRect(qr_x - 1.5 * mm, qr_y - 1.5 * mm,
                qr_size + 3 * mm, qr_size + 3 * mm, 1.5 * mm, fill=1, stroke=0)
    c.drawImage(ImageReader(io.BytesIO(qr_bytes)), qr_x, qr_y, qr_size, qr_size)

    c.setFillColor(WHITE)
    c.setFont('Helvetica-Bold', 5.5)
    c.drawCentredString(right_x + RIGHT_W / 2, qr_y - 4 * mm, 'SCAN TO VERIFY')
    c.setFont('Helvetica', 4.5)
    c.drawCentredString(right_x + RIGHT_W / 2, qr_y - 6.5 * mm, 'YOUR TICKET')

    c.setFillColor(GOLD_LIGHT)
    c.setFont('Helvetica-Oblique', 6.5)
    c.drawCentredString(right_x + RIGHT_W / 2, 8 * mm, 'Celebrating')
    c.drawCentredString(right_x + RIGHT_W / 2, 5 * mm, 'Excellence')

    # ════════════════════════════════════════════════════════════════════════
    # CENTRE PANEL — cream background with ticket details
    # ════════════════════════════════════════════════════════════════════════
    mid_x = LEFT_W
    c.setFillColor(CREAM)
    c.rect(mid_x, 0, MID_W, PAGE_H, fill=1, stroke=0)

    # Watermark logo
    if os.path.exists(logo_path):
        wm_size = 50 * mm
        wm_x = mid_x + (MID_W - wm_size) / 2
        wm_y = (PAGE_H - wm_size) / 2
        c.saveState()
        c.setFillAlpha(0.07)
        c.drawImage(
            ImageReader(logo_path),
            wm_x, wm_y, wm_size, wm_size,
            preserveAspectRatio=True, mask='auto',
        )
        c.restoreState()

    # Gold top + bottom stripes
    c.setFillColor(GOLD)
    c.rect(mid_x, PAGE_H - 4 * mm, MID_W, 4 * mm, fill=1, stroke=0)
    c.rect(mid_x, 0, MID_W, 4 * mm, fill=1, stroke=0)

    # ── Header ───────────────────────────────────────────────────────────────
    header_top = PAGE_H - 4 * mm - 5 * mm

    c.setFillColor(DARK_TEXT)
    c.setFont('Helvetica-Bold', 6)
    c.drawCentredString(mid_x + MID_W / 2, header_top, 'PANDORA AWARDS  ·  8TH EDITION')

    c.setFont('Helvetica-Bold', 10.5)
    c.drawCentredString(mid_x + MID_W / 2, header_top - 7 * mm, 'PANDORA AWARD 8TH EDITION E-TICKET')

    c.setStrokeColor(GOLD)
    c.setLineWidth(0.8)
    c.line(mid_x + 6 * mm, header_top - 9 * mm, mid_x + MID_W - 6 * mm, header_top - 9 * mm)

    c.setFillColor(GREY_TEXT)
    c.setFont('Helvetica', 6.5)
    c.drawCentredString(mid_x + MID_W / 2, header_top - 12.5 * mm, 'YOUR TICKET IS VALID')

    # ── Two-column guest details ──────────────────────────────────────────────
    col1_x = mid_x + 5 * mm
    col2_x = mid_x + MID_W / 2 + 3 * mm
    row1_y = header_top - 20 * mm
    row2_y = row1_y - 9 * mm
    row3_y = row2_y - 9 * mm

    def draw_field(x, y, label, value, max_chars=28):
        c.setFillColor(GOLD)
        c.setFont('Helvetica-Bold', 5.5)
        c.drawString(x + 5 * mm, y, label)
        c.setFillColor(DARK_TEXT)
        c.setFont('Helvetica', 7)
        c.drawString(x + 5 * mm, y - 4 * mm, str(value)[:max_chars])

    def draw_icon(x, y, color=None):
        ic = color or GOLD
        c.setFillColor(ic)
        c.circle(x + 2 * mm, y - 1.5 * mm, 2 * mm, fill=1, stroke=0)

    # Col 1
    draw_icon(col1_x, row1_y)
    draw_field(col1_x, row1_y, 'FULL NAME', ticket.guest.full_name)

    draw_icon(col1_x, row2_y)
    draw_field(col1_x, row2_y, 'EMAIL ADDRESS',
               ticket.guest.email if ticket.guest.email else ticket.guest.phone_number)

    draw_icon(col1_x, row3_y, colors.HexColor('#8a6400'))
    draw_field(col1_x, row3_y, 'TICKET TYPE', ticket.ticket_type.name)

    # Col 2
    draw_icon(col2_x, row1_y)
    draw_field(col2_x, row1_y, 'EVENT DATE',
               ticket.event.event_date.strftime('Sunday, %d %B %Y'))

    draw_icon(col2_x, row2_y, colors.HexColor('#8b0000'))
    draw_field(col2_x, row2_y, 'VENUE', 'A Class Event Center (Sapphire Hall)', max_chars=32)
    c.setFillColor(GREY_TEXT)
    c.setFont('Helvetica', 5.5)
    c.drawString(col2_x + 5 * mm, row2_y - 8.5 * mm, 'Along Kashmiri Ibrahim Way, Maitama')
    c.drawString(col2_x + 5 * mm, row2_y - 11.5 * mm, 'Abuja FCT Nigeria')

    draw_icon(col2_x, row3_y, colors.HexColor('#1a3a00'))
    draw_field(col2_x, row3_y, 'TICKET NO.', ticket.ticket_number)

    # ── Ticket type badge at bottom ───────────────────────────────────────────
    badge_y = 5.5 * mm
    price_map = {
        'REGULAR':            ('REGULAR',            '₦30,000'),
        'VIP':                ('VIP',                '₦100,000'),
        'SPECIAL GUEST SEAT': ('SPECIAL GUEST SEAT', '₦300,000'),
        'GOLD TABLE':         ('GOLD TABLE',         '₦800,000'),
        'MEDIA':              ('MEDIA',              'PRESS'),
        'STAFF':              ('STAFF',              'CREW'),
    }
    ttype = ticket.ticket_type.name.upper()
    badge_data = price_map.get(ttype)
    if badge_data:
        b_label, b_price = badge_data
        b_w = 28 * mm
        b_x = mid_x + (MID_W - b_w) / 2
        c.setFillColor(DARK_GREEN)
        c.roundRect(b_x, badge_y - 1 * mm, b_w, 7 * mm, 1.5 * mm, fill=1, stroke=0)
        c.setStrokeColor(GOLD)
        c.setLineWidth(0.5)
        c.roundRect(b_x, badge_y - 1 * mm, b_w, 7 * mm, 1.5 * mm, fill=0, stroke=1)
        c.setFillColor(GOLD)
        c.setFont('Helvetica-Bold', 5)
        c.drawCentredString(b_x + b_w / 2, badge_y + 3.5 * mm, b_label)
        c.setFillColor(WHITE)
        c.setFont('Helvetica-Bold', 7)
        c.drawCentredString(b_x + b_w / 2, badge_y + 0.5 * mm, b_price)

    # Ticket number small at bottom left
    c.setFillColor(GREY_TEXT)
    c.setFont('Helvetica', 5)
    c.drawString(mid_x + 5 * mm, 5.5 * mm, f'No. {ticket.ticket_number}')

    c.save()
    return buffer.getvalue()


def _draw_photo_placeholder(c, x, y, w, h):
    from reportlab.lib import colors
    c.setFillColor(colors.HexColor('#2a1500'))
    c.rect(x, y, w, h, fill=1, stroke=0)
    c.setFillColor(colors.HexColor('#c9960c'))
    c.setFont('Helvetica', 8)
    c.drawCentredString(x + w / 2, y + h / 2, 'PHOTO')

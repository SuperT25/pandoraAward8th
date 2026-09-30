# 🏆 Pandora Awards E-Ticket System
**8th Edition — Live in Abuja 2026**

## Quick Start

```powershell
# 1. Activate virtual environment
.\venv\Scripts\Activate

# 2. Run the development server
python manage.py runserver

# 3. Open in browser
# http://127.0.0.1:8000/
```

## Default Login

| Username | Password | Role |
|---|---|---|
| `pandoraadmin` | `Pandora@2026!` | Super Admin |

> ⚠️ **Change this password immediately after first login.**

---

## Event Details (Pre-loaded)

- **Event:** Pandora Awards 8th Edition
- **Date:** Sunday, 29th November 2026
- **Venue:** A Class Event Center, Sapphire Hall, Maitama, Abuja
- **Red Carpet:** 4:00 PM | **Main Event:** 6:00 PM

### Ticket Types (Pre-loaded)
| Type | Category |
|---|---|
| Regular | Standard |
| VIP | Premium |
| Special Guest Seat | Exclusive |
| Gold Table | Table Reservation |
| Media | Press |
| Staff | Event Staff |

---

## URL Structure

| URL | Description |
|---|---|
| `/login/` | Login page |
| `/dashboard/` | Main dashboard with stats |
| `/guests/` | All registered guests |
| `/guests/create/` | Register new guest + generate ticket |
| `/tickets/` | All tickets |
| `/tickets/<id>/` | Ticket detail + QR |
| `/tickets/<id>/download/` | Download PDF ticket |
| `/verify/` | **Verification portal** (main entrance page) |
| `/verify/search/` | POST endpoint for ticket/phone search |
| `/verify/qr/<token>/` | QR code scan endpoint |
| `/walk-in/` | Walk-in guest registration |
| `/reports/` | Reports + CSV export |
| `/logs/` | Verification activity log |
| `/events/` | Event management |
| `/ticket-types/` | Ticket type management |
| `/staff/` | Staff account management |

---

## User Roles

| Role | Permissions |
|---|---|
| **Super Admin** | Full access — events, staff, tickets, reports |
| **Ticket Admin** | Register guests, manage tickets, reports |
| **Verification Staff** | Search + verify + check-in only |
| **Walk-In Staff** | Walk-in registration + verify + check-in |

---

## Workflow

### Pre-Registered Guest
1. Admin registers guest at `/guests/create/`
2. System auto-generates ticket number + QR code
3. Admin downloads PDF ticket and sends via WhatsApp/email
4. At event: staff opens `/verify/`, enters ticket number or phone
5. Staff sees green VALID screen with guest photo
6. Staff presses **CHECK IN** → ticket becomes USED

### Walk-In Guest
1. Guest pays Pandora representative directly (outside system)
2. Staff opens `/walk-in/`, enters guest details + photo
3. System generates ticket instantly
4. Guest is shown verify screen → staff presses **CHECK IN**

---

## Security Features
- Role-based access control (4 roles)
- CSRF protection on all forms
- Atomic check-in transaction (prevents double check-in)
- `select_for_update()` database row lock during check-in
- Secure random ticket numbers (PDR26-XXXXXX format)
- UUID4 QR tokens — no personal data in QR code
- Photo upload validation (type + size)
- All verification actions logged with timestamp + IP

---

## Production Deployment Notes
1. Set `DEBUG = False` in settings
2. Set a real `SECRET_KEY` via environment variable
3. Configure PostgreSQL database
4. Enable HTTPS and uncomment security headers in settings
5. Run `python manage.py collectstatic`
6. Use gunicorn + nginx

---

## Contact
📧 info.pandoraawards@gmail.com  
📞 +234 814 639 6555 / 08161127610  
📲 @pandora_Awards

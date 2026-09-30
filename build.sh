#!/usr/bin/env bash
# Render build script — runs once at each deploy

set -o errexit   # exit immediately on any error

echo "==> Installing Python dependencies..."
pip install -r requirements.txt

echo "==> Collecting static files..."
python manage.py collectstatic --no-input

echo "==> Running database migrations..."
python manage.py migrate --no-input

echo "==> Seeding initial event data (safe — skips if already exists)..."
python manage.py seed_data

echo "==> Regenerating QR codes with live verify URL..."
python manage.py regenerate_qr

echo "==> Build complete."

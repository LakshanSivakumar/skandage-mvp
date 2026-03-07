#!/usr/bin/env bash
# exit on error
set -o errexit

pip install -r requirements.txt

# Download Tailwind CLI and build CSS
curl -sLO https://github.com/tailwindlabs/tailwindcss/releases/latest/download/tailwindcss-linux-x64
chmod +x tailwindcss-linux-x64
./tailwindcss-linux-x64 -i ./core/tailwind_input.css -o ./core/static/css/output.css --minify

# Convert static assets
python manage.py collectstatic --no-input

# Apply database migrations
python manage.py migrate

playwright install chromium
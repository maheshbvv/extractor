#!/bin/bash
apt-get install -y tesseract-ocr 2>/dev/null || true
pip install gunicorn
gunicorn app:app --bind 0.0.0.0:10000

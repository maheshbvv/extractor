from flask import Flask, request, jsonify, send_from_directory
import cv2
import pytesseract
import re
import numpy as np
import base64
import os

# If tesseract path is required (Windows example):
# pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

app = Flask(__name__, static_folder=".")


def find_indian_numbers(text):
    """
    Extract Indian mobile numbers in any common format:
      +91 85899 46512 / +9199477 19883 / 9947178151
    Also handles OCR artifacts like +91'79024 (apostrophe instead of space).
    """
    # Fix OCR artifact: apostrophe or backtick between +91 and digits
    text = re.sub(r"(\+91)['\`]", r'\1 ', text)
    results = []
    for m in re.finditer(r'(?<!\d)(?:\+91|91)?[\s-]?([6-9][\d\s-]{9,14})', text):
        digits = re.sub(r'\D', '', m.group(0))
        if digits.startswith('91') and len(digits) == 12:
            results.append('+91' + digits[2:])
        elif len(digits) == 10 and digits[0] in '6789':
            results.append('+91' + digits)
    return sorted(set(results))


def preprocess(img):
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    if np.mean(gray) < 127:
        # Dark background (e.g. dark-mode screenshots): invert so text is black on white
        gray = cv2.bitwise_not(gray)
    else:
        # Light background: threshold to remove noise
        gray = cv2.threshold(gray, 150, 255, cv2.THRESH_BINARY)[1]
    return gray


def extract_from_bytes(file_bytes):
    np_arr = np.frombuffer(file_bytes, np.uint8)
    img = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
    if img is None:
        return [], "", "Could not decode image"
    processed = preprocess(img)
    text = pytesseract.image_to_string(processed)
    numbers = find_indian_numbers(text)
    return numbers, text.strip(), None


@app.route("/")
def index():
    return send_from_directory(".", "index.html")


@app.route("/extract", methods=["POST"])
def extract():
    files = request.files.getlist("images")
    if not files:
        return jsonify({"error": "No images uploaded"}), 400

    results = []
    for f in files:
        file_bytes = f.read()

        ext = os.path.splitext(f.filename)[1].lower().lstrip(".")
        mime = "jpeg" if ext in ("jpg", "jpeg") else ext
        b64 = base64.b64encode(file_bytes).decode()
        preview = f"data:image/{mime};base64,{b64}"

        numbers, text, error = extract_from_bytes(file_bytes)
        results.append({
            "filename": f.filename,
            "preview": preview,
            "numbers": numbers,
            "text": text,
            "error": error,
        })

    all_numbers = sorted(set(n for r in results for n in r["numbers"]))
    return jsonify({"results": results, "all_numbers": all_numbers})


if __name__ == "__main__":
    print("Starting server at http://localhost:8080")
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))

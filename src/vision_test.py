"""
OCR tuning: capture the active window once, then run OCR on it with
several different preprocessing settings so we can compare which
produces the cleanest text.
"""

import subprocess
import pytesseract
from PIL import Image

from src.tools.vision_tools import _get_active_window_bounds

CAPTURE_PATH = "ocr_tuning_capture.png"


def capture_active_window():
    bounds = _get_active_window_bounds()
    if bounds:
        x, y, w, h = bounds
        args = ["screencapture", "-o", "-x", "-R", f"{x},{y},{w},{h}", CAPTURE_PATH]
    else:
        args = ["screencapture", "-o", "-x", CAPTURE_PATH]
    subprocess.run(args, capture_output=True, timeout=15)
    return Image.open(CAPTURE_PATH)


def variant_raw(image):
    """No preprocessing at all — baseline."""
    return image


def variant_current(image):
    """What we use now: grayscale, 2x upscale, threshold at 150."""
    gray = image.convert("L")
    w, h = gray.size
    up = gray.resize((w * 2, h * 2), Image.LANCZOS)
    return up.point(lambda p: 0 if p < 150 else 255)


def variant_grayscale_only(image):
    """Grayscale + upscale, but no thresholding."""
    gray = image.convert("L")
    w, h = gray.size
    return gray.resize((w * 2, h * 2), Image.LANCZOS)


def variant_inverted(image):
    """Dark themes are light-on-dark; OCR expects dark-on-light.
    Inverting may help significantly for a dark VS Code theme."""
    gray = image.convert("L")
    w, h = gray.size
    up = gray.resize((w * 2, h * 2), Image.LANCZOS)
    inverted = up.point(lambda p: 255 - p)
    return inverted.point(lambda p: 0 if p < 150 else 255)


VARIANTS = {
    "raw (no preprocessing)": variant_raw,
    "current (gray+2x+threshold)": variant_current,
    "grayscale + upscale only": variant_grayscale_only,
    "inverted (for dark themes)": variant_inverted,
}

print("Capturing active window in 3 seconds — click the window you want to test...")
import time
time.sleep(3)

image = capture_active_window()
print(f"Captured. Size: {image.size}\n")

for name, func in VARIANTS.items():
    processed = func(image)
    text = pytesseract.image_to_string(processed).strip()
    char_count = len(text)
    print("=" * 60)
    print(f"VARIANT: {name}  ({char_count} chars extracted)")
    print("=" * 60)
    print(text[:600] if text else "(nothing detected)")
    print()
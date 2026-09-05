"""
Screen perception tool: takes a screenshot and extracts visible text
via OCR. Moondream (vision model) was tested and dropped — its
descriptions were unreliable, hallucinating scenes unrelated to the
actual screen content. OCR, while imperfect, extracts real text
reliably enough to be useful.
"""

import pyautogui
import pytesseract
from PIL import Image

SCREENSHOT_PATH = "last_screenshot.png"


def _preprocess_for_ocr(image: Image.Image) -> Image.Image:
    """Clean up a screenshot to make text extraction more reliable.

    - Grayscale: color isn't needed for reading text and adds noise.
    - Upscale 2x: small UI text is often too small to read at native size.
    - Threshold: turns it into clean black-on-white, what OCR expects.
    """
    gray = image.convert("L")
    width, height = gray.size
    upscaled = gray.resize((width * 2, height * 2), Image.LANCZOS)
    return upscaled.point(lambda pixel: 0 if pixel < 150 else 255)


def read_screen(reason: str = "") -> str:
    """Take a screenshot and return the text visible on screen.
    'reason' is unused — it exists only because local models seem to
    invoke tools more reliably when there's at least one parameter."""
    try:
        screenshot = pyautogui.screenshot()
        screenshot.save(SCREENSHOT_PATH)
        cleaned = _preprocess_for_ocr(screenshot)
        text = pytesseract.image_to_string(cleaned).strip()
        return text if text else "(no readable text detected on screen)"
    except Exception as e:
        return f"Error reading screen: {e}"


READ_SCREEN_SCHEMA = {
    "name": "read_screen",
    "description": (
        "Take a screenshot of the user's current screen and extract any "
        "visible text using OCR. Use this when the user asks what's on "
        "their screen, what they're looking at, or to read/summarize "
        "something currently displayed."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "reason": {
                "type": "string",
                "description": "Brief reason for reading the screen, e.g. 'user asked what's displayed'.",
            }
        },
        "required": [],
    },
}
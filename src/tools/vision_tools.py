import subprocess
import time

import pytesseract
from PIL import Image

from ..hud_server import set_status

SCREENSHOT_PATH = "last_screenshot.png"
CAPTURE_DELAY_SECONDS = 3

# Returns a flat list: name1, x1, y1, w1, h1, name2, x2, y2, w2, h2, ...
_BOUNDS_SCRIPT = (
    'tell app "System Events" to tell '
    "(first application process whose frontmost is true) to "
    "get {name, position, size} of every window"
)


def _get_active_window_bounds():
    """Return (x, y, width, height) of the largest window of the
    frontmost app, or None if it can't be determined."""
    try:
        result = subprocess.run(
            ["osascript", "-e", _BOUNDS_SCRIPT],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode != 0:
            return None

        parts = [p.strip() for p in result.stdout.strip().split(",")]
        # Numeric values come after the window names; collect them in order
        numbers = [int(p) for p in parts if p.lstrip("-").isdigit()]

        # Numbers arrive as all positions first, then all sizes:
        # x1, y1, x2, y2, ..., w1, h1, w2, h2, ...
        if len(numbers) < 4 or len(numbers) % 4 != 0:
            return None

        count = len(numbers) // 4
        positions = numbers[: count * 2]
        sizes = numbers[count * 2 :]

        best = None
        best_area = 0
        for i in range(count):
            x, y = positions[i * 2], positions[i * 2 + 1]
            w, h = sizes[i * 2], sizes[i * 2 + 1]
            area = w * h
            if area > best_area:
                best_area = area
                best = (x, y, w, h)
        return best
    except Exception:
        return None


def _preprocess_for_ocr(image: Image.Image) -> Image.Image:
    """Grayscale + 2x upscale. No thresholding — see module docstring."""
    gray = image.convert("L")
    width, height = gray.size
    return gray.resize((width * 2, height * 2), Image.LANCZOS)


def _clean_ocr_text(text: str) -> str:
    """Strip the noise OCR produces from icons, borders, and UI chrome.

    Tesseract emits short garbage fragments for anything that isn't
    real text — decorative graphics, toolbar icons, window borders.
    Filtering here is more reliable than asking the model to ignore
    them, which it doesn't consistently do.
    """
    kept = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue

        # Drop very short fragments unless they're plausible words/numbers
        if len(line) <= 3 and not line.isalnum():
            continue

        # Drop lines that are mostly punctuation/symbols rather than letters
        letters = sum(c.isalnum() or c.isspace() for c in line)
        if letters / len(line) < 0.6:
            continue

        kept.append(line)

    return "\n".join(kept)


def read_screen(reason: str = "") -> str:
    """Capture the active window and return the text visible in it.
    'reason' is unused — it exists only because local models seem to
    invoke tools more reliably when there's at least one parameter."""
    try:
        # Give the user time to click onto whatever they want read,
        # since using the HUD makes the browser frontmost.
        set_status(
            "reading screen",
            f"switch windows now — capturing in {CAPTURE_DELAY_SECONDS}s",
        )
        time.sleep(CAPTURE_DELAY_SECONDS)

        bounds = _get_active_window_bounds()

        if bounds:
            x, y, w, h = bounds
            capture_args = [
                "screencapture", "-o", "-x", "-R", f"{x},{y},{w},{h}", SCREENSHOT_PATH
            ]
        else:
            # Fall back to full screen if window detection failed
            capture_args = ["screencapture", "-o", "-x", SCREENSHOT_PATH]

        result = subprocess.run(capture_args, capture_output=True, text=True, timeout=15)
        if result.returncode != 0:
            return f"Error capturing screen: {result.stderr.strip()}"

        image = Image.open(SCREENSHOT_PATH)
        cleaned = _preprocess_for_ocr(image)
        text = _clean_ocr_text(pytesseract.image_to_string(cleaned))
        return text if text else "(no readable text detected on screen)"
    except Exception as e:
        return f"Error reading screen: {e}"


READ_SCREEN_SCHEMA = {
    "name": "read_screen",
    "description": (
        "Capture the user's currently active window and extract the text "
        "visible in it using OCR. Use this when the user asks what's on "
        "their screen, what they're looking at, or to read or summarize "
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
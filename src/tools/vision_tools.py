import pyautogui
import pytesseract
from PIL import Image

SCREENSHOT_PATH = "last_screenshot.png"


def _preprocess_for_ocr(image: Image.Image) -> Image.Image:
    """Grayscale + upscale + threshold to make small UI text readable."""
    gray = image.convert("L")
    width, height = gray.size
    upscaled = gray.resize((width * 2, height * 2), Image.LANCZOS)
    return upscaled.point(lambda pixel: 0 if pixel < 150 else 255)


def read_screen() -> str:
    """Take a screenshot and return the text visible on screen."""
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
        "properties": {},
        "required": [],
    },
}
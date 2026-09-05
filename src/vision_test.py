import pyautogui
import pytesseract
from PIL import Image

SCREENSHOT_PATH = "test_screenshot.png"


def preprocess_for_ocr(image: Image.Image) -> Image.Image:
    """Clean up a screenshot to make text extraction more reliable.

    - Convert to grayscale: color info isn't needed for reading text,
      and removing it reduces noise Tesseract has to deal with.
    - Upscale 2x: small UI text (status bars, icons) is often too
      small for Tesseract to read reliably at native resolution.
    - Increase contrast via thresholding: turns the image into clean
      black-on-white, which is what OCR engines are tuned for.
    """
    gray = image.convert("L")
    width, height = gray.size
    upscaled = gray.resize((width * 2, height * 2), Image.LANCZOS)
    # Simple threshold: anything darker than 150 becomes black, else white
    threshold = upscaled.point(lambda pixel: 0 if pixel < 150 else 255)
    return threshold


print("Taking screenshot...")
screenshot = pyautogui.screenshot()
screenshot.save(SCREENSHOT_PATH)
print(f"Saved to {SCREENSHOT_PATH}")

print("Preprocessing for OCR...")
cleaned = preprocess_for_ocr(screenshot)
cleaned.save("test_screenshot_cleaned.png")  # so you can look at it yourself

print("Running OCR...")
extracted_text = pytesseract.image_to_string(cleaned).strip()

print("\nOCR result:")
print(extracted_text if extracted_text else "(no text detected)")
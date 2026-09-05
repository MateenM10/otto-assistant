"""Test: can we detect the active window's position and size?"""

import pyautogui
import time

print("Click on the window you want to capture. Capturing in 3 seconds...")
time.sleep(3)

window = pyautogui.getActiveWindow()

if window is None:
    print("Could not detect active window.")
else:
    print(f"Window title: {window.title}")
    print(f"Position: left={window.left}, top={window.top}")
    print(f"Size: width={window.width}, height={window.height}")

    screenshot = pyautogui.screenshot(
        region=(window.left, window.top, window.width, window.height)
    )
    screenshot.save("window_test3.png")
    print("Saved cropped screenshot to window_test3.png")
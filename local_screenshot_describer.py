import os
import time
import pyautogui
from PIL import Image
import torch
from transformers import pipeline

# ——— CONFIG ———
# If you have a CUDA‑capable GPU, this will use it; otherwise it falls back to CPU.
DEVICE = 0 if torch.cuda.is_available() else -1

# How often to grab screenshots (in seconds). Set to None for one‑shot.
POLL_INTERVAL = None  # e.g. 5

# ——— SETUP CAPTIONER ———
captioner = pipeline(
    "image-to-text",
    model="nlpconnect/vit-gpt2-image-captioning",
    device=DEVICE
)

def capture_screenshot(region=None):
    """
    Captures a screenshot and returns a PIL.Image.
    If region=(x, y, w, h), only that area is grabbed.
    """
    img = pyautogui.screenshot(region=region)
    return img

def describe_image(img):
    """
    Feeds a PIL.Image into the HF caption pipeline
    and returns the generated text.
    """
    outputs = captioner(img, max_length=64, num_beams=4)
    return outputs[0]["generated_text"]

def main():
    try:
        while True:
            img = capture_screenshot()
            desc = describe_image(img)
            print(f"\n[{time.strftime('%H:%M:%S')}] Description:\n{desc}\n")
            if POLL_INTERVAL is None:
                break
            time.sleep(POLL_INTERVAL)
    except KeyboardInterrupt:
        print("✅ Exiting.")

if __name__ == "__main__":
    main()

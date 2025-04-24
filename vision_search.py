# Danzar/vision_search.py

import requests
from bs4 import BeautifulSoup
from transformers import BlipProcessor, BlipForConditionalGeneration
from PIL import Image
import os

# Load BLIP
processor = BlipProcessor.from_pretrained("Salesforce/blip-image-captioning-base")
model     = BlipForConditionalGeneration.from_pretrained("Salesforce/blip-image-captioning-base")

def caption_image(path: str) -> str:
    """
    Generate a natural-language caption for the local image file.
    """
    img = Image.open(path).convert("RGB")
    inputs = processor(img, return_tensors="pt")
    out    = model.generate(**inputs)
    return processor.decode(out[0], skip_special_tokens=True)

def reverse_image_search(path: str, max_results: int = 5) -> list[dict]:
    """
    Perform a simple reverse-image search using Google. Returns list of dicts:
    [{'title': ..., 'link': ...}, ...]
    """
    # Upload to a free image host or data URI
    # Here as a stub: we assume 'upload_to_imgur' returns a public URL
    from .utils import upload_to_imgur
    img_url = upload_to_imgur(path)

    google_url = f"https://www.google.com/searchbyimage?image_url={img_url}"
    headers    = {"User-Agent": "Mozilla/5.0"}
    resp       = requests.get(google_url, headers=headers)
    soup       = BeautifulSoup(resp.text, "html.parser")

    results = []
    for div in soup.select("div.r5a77d")[:max_results]:
        a = div.find("a")
        if a and a.text and a["href"]:
            results.append({"title": a.text.strip(), "link": a["href"]})
    return results

# Danzar/chatgpt_teacher.py
from playwright.sync_api import sync_playwright
import logging, time

logger = logging.getLogger(__name__)

def get_chatgpt_response(prompt: str, timeout_s: int = 60) -> str:
    """
    Sends `prompt` to ChatGPT web UI via Playwright, returns its answer text.
    Requires that you've previously saved auth.json (with your login).
    """
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        ctx     = browser.new_context(storage_state="auth.json")
        page    = ctx.new_page()
        page.goto("https://chat.openai.com/chat", wait_until="networkidle")
        # wait for the input area
        page.wait_for_selector("textarea")
        # type and send
        page.fill("textarea", prompt)
        page.keyboard.press("Enter")
        # wait for the new reply to appear
        start = time.time()
        while time.time() - start < timeout_s:
            # Chat messages have role="assistant" in their container
            replies = page.query_selector_all("div.role-assistant .markdown")
            if replies:
                # last one is the newest
                text = replies[-1].inner_text().strip()
                if text:
                    browser.close()
                    return text
            time.sleep(1)
        browser.close()
        raise RuntimeError("Timed out waiting for ChatGPT reply")

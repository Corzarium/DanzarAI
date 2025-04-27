# Danzar/chatgpt_teacher_async.py

import asyncio
import logging
from playwright.async_api import async_playwright, TimeoutError as PWTimeoutError

logger = logging.getLogger(__name__)

async def get_chatgpt_response_async(prompt: str, timeout_s: int = 90) -> str:
    """
    Automates the ChatGPT web UI to send `prompt` and return the assistant’s reply.
    """
    # 1) Start Playwright
    pw = await async_playwright().start()
    browser = await pw.chromium.launch(headless=True)

    try:
        # 2) Reuse your logged-in session
        ctx = await browser.new_context(storage_state="auth.json")
        page = await ctx.new_page()
        await page.bring_to_front()

        # 3) Navigate to the chat page (DOMContentLoaded only)
        await page.goto(
            "https://chat.openai.com/chat",
            wait_until="domcontentloaded",
            timeout=timeout_s * 1000
        )

        # 4) Locate the input element in priority order:
        #    a) ProseMirror wrapper
        pm = page.locator('#prompt-textarea')
        if await pm.count() > 0:
            target = pm.first
        else:
            #    b) <form> textarea
            ta = page.locator("form textarea")
            if await ta.count() > 0:
                target = ta.first
            else:
                #    c) ARIA contenteditable textbox
                tb = page.get_by_role("textbox")
                if await tb.count() > 0:
                    target = tb.first
                else:
                    raise RuntimeError("Could not find any chat input on the page")

        # 5) Focus & fill
        await target.wait_for(state="visible", timeout=timeout_s * 1000)
        await target.click()
        await target.fill(prompt)

        # 6) Submit via Ctrl+Enter
        await target.press("Control+Enter")

        # 7) Wait for the assistant’s final message to stabilize
        start_time = asyncio.get_event_loop().time()
        last_text = ""
        while True:
            msgs = await page.query_selector_all("div.role-assistant .markdown")
            if msgs:
                text = (await msgs[-1].inner_text()).strip()
                if text and text == last_text:
                    return text
                last_text = text
            if asyncio.get_event_loop().time() - start_time > timeout_s:
                raise PWTimeoutError(f"Timed out after {timeout_s}s waiting for reply")
            await asyncio.sleep(0.5)

    finally:
        # 8) Clean up
        await browser.close()
        await pw.stop()

#!/usr/bin/env python
# chatgpt_selenium.py

import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

def send_and_get_reply(prompt: str, timeout: int = 30) -> str:
    """
    Attaches to an existing ChatGPT browser session, types `prompt`,
    waits for the reply, and returns it as a string.
    """
    # 1) Attach to Chrome (must be launched with --remote-debugging-port=9222)
    opts = webdriver.ChromeOptions()
    opts.add_experimental_option("debuggerAddress", "127.0.0.1:9222")
    driver = webdriver.Chrome(options=opts)
    wait = WebDriverWait(driver, timeout)

    try:
        # 2) Switch to the ChatGPT tab
        for handle in driver.window_handles:
            driver.switch_to.window(handle)
            url = driver.current_url
            if "chatgpt.com" in url or "chat.openai.com" in url:
                break
        else:
            raise RuntimeError("No ChatGPT tab found")

        # 3) Find the ProseMirror editor by ID
        editor = wait.until(EC.presence_of_element_located(
            (By.CSS_SELECTOR, "#prompt-textarea")
        ))

        # 4) Count paragraphs before sending
        before = driver.find_elements(By.CSS_SELECTOR, "div.markdown.prose p")
        before_count = len(before)

        # 5) Focus & inject prompt via JS
        driver.execute_script("""
            const ed = arguments[0];
            ed.innerText = '';
            ed.innerText = arguments[1];
            ed.dispatchEvent(new InputEvent('input', { bubbles: true }));
        """, editor, prompt)

        # 6) Click “Send”
        send_btn = wait.until(EC.element_to_be_clickable(
            (By.CSS_SELECTOR, "button[data-testid='send-button']")
        ))
        send_btn.click()

        # 7) Wait for new paragraphs to appear
        wait.until(lambda d: len(d.find_elements(
            By.CSS_SELECTOR, "div.markdown.prose p"
        )) > before_count)

        # 8) Grab and return the last paragraph’s text
        all_ps = driver.find_elements(By.CSS_SELECTOR, "div.markdown.prose p")
        reply = all_ps[-1].text.strip()
        return reply

    finally:
        driver.quit()


if __name__ == "__main__":
    question = "Hey ChatGPT, what's 2+2?"
    answer = send_and_get_reply(question)
    print(f"🤖 ChatGPT answered: {answer}")
    # Here you could hand `answer` off to your DanzarAI logic instead of printing.

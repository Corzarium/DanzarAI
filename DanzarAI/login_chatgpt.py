# login_playwright.py
from playwright.sync_api import sync_playwright

def main():
    with sync_playwright() as pw:
        ctx = pw.chromium.launch_persistent_context(
            channel="chrome",
            user_data_dir="user-data",        # your copy of Default
            headless=False,
            ignore_https_errors=True,
            viewport={"width":1280,"height":800},
            args=["--disable-blink-features=AutomationControlled"],
            ignore_default_args=["--enable-automation"],
        )

        # no need to log in—you're already authenticated
        page = ctx.pages[0]
        page.goto("https://chat.openai.com/chat", wait_until="networkidle", timeout=60000)
        print("✅ Loaded ChatGPT with your existing login!")

        # now save it into auth.json for true headless reuse
        ctx.storage_state(path="auth.json", indexed_db=True)
        print("✨ auth.json saved—headless scripts can now use it.")

        ctx.close()

if __name__ == "__main__":
    main()

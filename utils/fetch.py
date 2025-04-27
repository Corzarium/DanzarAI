import requests
from bs4 import BeautifulSoup

BASE_URL = "https://pathofexile2.wiki.fextralife.com/{}"

def fetch_page(slug: str) -> str|None:
    resp = requests.get(BASE_URL.format(slug))
    if resp.status_code != 200:
        return None
    soup = BeautifulSoup(resp.text, "lxml")
    main = soup.find("div", class_="mw-parser-output") or soup.body
    return main.get_text(separator="\n")

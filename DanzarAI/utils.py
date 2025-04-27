# Danzar/utils.py

import requests

def upload_to_imgur(path: str) -> str:
    """
    Upload a local file to Imgur anonymously.
    Requires IMGUR_CLIENT_ID env var.
    """
    client_id = os.getenv("IMGUR_CLIENT_ID")
    if not client_id:
        raise RuntimeError("Set IMGUR_CLIENT_ID to upload images")
    headers = {"Authorization": f"Client-ID {client_id}"}
    with open(path, "rb") as f:
        data = {"image": f.read()}
    resp = requests.post("https://api.imgur.com/3/image", headers=headers, files=data)
    j    = resp.json()
    if not j.get("success"):
        raise RuntimeError("Imgur upload failed")
    return j["data"]["link"]

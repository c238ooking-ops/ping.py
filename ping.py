import hashlib
import os
import re
import sys
import time
import requests

# ---------------------------------------------------------
# ROOT FOLDER / PAGE LINK:
ROOT_URL = "https://gofile.io/d/OBVVp1LI#page"
# ---------------------------------------------------------

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
LANG = "en-US"
SALT = "9844d94d963d30"

def generate_website_token(account_token=""):
    """Computes the dynamic X-Website-Token required to browse folders as a free web client."""
    time_slot = int(time.time()) // 14400
    raw_str = f"{USER_AGENT}::{LANG}::{account_token}::{time_slot}::{SALT}"
    return hashlib.sha256(raw_str.encode("utf-8")).hexdigest()

def get_guest_token():
    """Generates a fresh guest session token."""
    try:
        res = requests.post(
            "https://api.gofile.io/accounts",
            headers={"User-Agent": USER_AGENT, "Accept": "*/*"},
            timeout=10
        ).json()
        if res.get("status") == "ok":
            return res["data"]["token"]
    except Exception as e:
        print(f"⚠️ Guest account token fallback: {e}")
    return ""

def extract_content_id(url):
    url = url.strip()
    match = re.search(r'([0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}|[a-zA-Z0-9_-]{5,})', url.split('/')[-1].split('?')[0])
    return match.group(1) if match else url.split('/')[-1]

def ping_direct_file(url, name=""):
    token = get_guest_token()
    headers = {
        "User-Agent": USER_AGENT,
        "Range": "bytes=0-1024",
        "Referer": "https://gofile.io/",
        "X-BL": LANG,
        "X-Website-Token": generate_website_token(token)
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"

    try:
        resp = requests.get(url, headers=headers, timeout=15)
        print(f"      📄 Active ({resp.status_code}): {name or url}")
    except Exception as e:
        print(f"      ❌ Error pinging file {name}: {e}")

def crawl_and_ping(content_id, depth=0):
    indent = "  " * depth
    print(f"{indent}📂 Scanning Folder [{content_id}]...")

    token = get_guest_token()
    wt = generate_website_token(token)

    headers = {
        "User-Agent": USER_AGENT,
        "X-BL": LANG,
        "X-Website-Token": wt,
        "Accept": "*/*",
        "Referer": f"https://gofile.io/d/{content_id}"
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"

    try:
        api_url = f"https://api.gofile.io/contents/{content_id}?contentFilter=&page=1&pageSize=1000&sortField=createTime&sortDirection=-1"
        resp = requests.get(api_url, headers=headers, timeout=15).json()

        if resp.get("status") != "ok":
            print(f"{indent}⚠️ Could not read folder [{content_id}]: {resp.get('status')}")
            return

        data = resp.get("data", {})
        children = data.get("children", {})

        if data.get("type") == "file":
            ping_direct_file(data.get("link"), data.get("name"))
            return

        for item_id, item in children.items():
            item_type = item.get("type")
            item_name = item.get("name", "Unnamed")

            if item_type == "folder":
                crawl_and_ping(item_id, depth + 1)
            else:
                download_link = item.get("link")
                if download_link:
                    ping_direct_file(download_link, item_name)
                    time.sleep(0.5)
    except Exception as e:
        print(f"{indent}❌ Error crawling {content_id}: {e}")

def main():
    root_id = extract_content_id(ROOT_URL)
    print(f"🚀 Starting Keep-Alive Crawl for Root Folder ID: {root_id}\n")
    crawl_and_ping(root_id)
    print("\n🎉 Entire storage hierarchy recursively scanned and pinged!")

if __name__ == "__main__":
    main()

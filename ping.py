import os
import re
import sys
import time
import requests

# ---------------------------------------------------------
# PASTE YOUR ROOT FOLDER LINK HERE:
ROOT_URL = "https://gofile.io/d/OBVVp1LI#page"
# ---------------------------------------------------------

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Range": "bytes=0-1024"
}

GOFILE_TOKEN = os.environ.get("GOFILE_TOKEN", "").strip()
if GOFILE_TOKEN:
    HEADERS["Authorization"] = f"Bearer {GOFILE_TOKEN}"

def extract_content_id(url):
    url = url.strip()
    match = re.search(r'([0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}|[a-zA-Z0-9_-]{5,})', url.split('/')[-1].split('?')[0])
    return match.group(1) if match else url.split('/')[-1]

def ping_direct_file(url, name=""):
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        print(f"      📄 Active ({resp.status_code}): {name or url}")
    except Exception as e:
        print(f"      ❌ Error pinging file {name}: {e}")

def crawl_and_ping(content_id, depth=0):
    indent = "  " * depth
    print(f"{indent}📂 Scanning Folder [{content_id}]...")
    try:
        api_url = f"https://api.gofile.io/contents/{content_id}"
        resp = requests.get(api_url, headers=HEADERS, timeout=15).json()

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
                    time.sleep(0.3)
    except Exception as e:
        print(f"{indent}❌ Error crawling {content_id}: {e}")

def main():
    if "YOUR_ACTUAL_LINK_HERE" in ROOT_URL or not ROOT_URL.strip():
        print("❌ Please update ROOT_URL with your Gofile link.")
        sys.exit(1)

    root_id = extract_content_id(ROOT_URL)
    print(f"🚀 Starting Keep-Alive Crawl for Root Folder ID: {root_id}\n")
    crawl_and_ping(root_id)
    print("\n🎉 Entire storage hierarchy recursively scanned and pinged!")

if __name__ == "__main__":
    main()

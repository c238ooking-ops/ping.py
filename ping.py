import os
import re
import sys
import time
import requests

# ---------------------------------------------------------
# ROOT FOLDER / PAGE LINK:
ROOT_URL = "https://gofile.io/d/OBVVp1LI#page"
# ---------------------------------------------------------

BASE_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "*/*",
    "Sec-Fetch-Site": "cross-site",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Dest": "empty",
}

def create_fresh_guest_token():
    """Generates a brand new anonymous guest account session on Gofile."""
    try:
        res = requests.post("https://api.gofile.io/accounts", headers=BASE_HEADERS, timeout=10).json()
        if res.get("status") == "ok":
            return res["data"]["token"]
    except Exception as e:
        print(f"⚠️ Guest session creation error: {e}")
    return None

def extract_content_id(url):
    url = url.strip()
    match = re.search(r'([0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}|[a-zA-Z0-9_-]{5,})', url.split('/')[-1].split('?')[0])
    return match.group(1) if match else url.split('/')[-1]

def ping_direct_file(url, name=""):
    # Generate a fresh guest session token per file ping
    token = create_fresh_guest_token()
    headers = {
        **BASE_HEADERS,
        "Range": "bytes=0-1024",
        "Referer": "https://gofile.io/"
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"

    try:
        resp = requests.get(url, headers=headers, timeout=15)
        print(f"      📄 Active ({resp.status_code}): {name or url} [Guest Session Reset]")
    except Exception as e:
        print(f"      ❌ Error pinging file {name}: {e}")

def crawl_and_ping(content_id, depth=0, folder_token=None):
    indent = "  " * depth
    print(f"{indent}📂 Scanning Folder [{content_id}]...")

    headers = {**BASE_HEADERS}
    if folder_token:
        headers["Authorization"] = f"Bearer {folder_token}"

    try:
        api_url = f"https://api.gofile.io/contents/{content_id}"
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
                crawl_and_ping(item_id, depth + 1, folder_token)
            else:
                download_link = item.get("link")
                if download_link:
                    ping_direct_file(download_link, item_name)
                    time.sleep(0.5)
    except Exception as e:
        print(f"{indent}❌ Error crawling {content_id}: {e}")

def main():
    root_id = extract_content_id(ROOT_URL)
    print(f"🚀 Starting Keep-Alive with Dynamic Guest Sessions for: {root_id}\n")
    
    # 1. Acquire initial token to read folder index
    initial_token = create_fresh_guest_token()
    if not initial_token:
        # Fallback to repository secret if public guest creation fails
        initial_token = os.environ.get("GOFILE_TOKEN", "").strip()

    crawl_and_ping(root_id, folder_token=initial_token)
    print("\n🎉 Entire storage hierarchy recursively scanned and pinged with unique guest sessions!")

if __name__ == "__main__":
    main()

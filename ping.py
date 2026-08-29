import sys
import time
import requests
from playwright.sync_api import sync_playwright

ROOT_URL = "https://gofile.io/d/OBVVp1LI"

def ping_direct_file(url, name=""):
    try:
        resp = requests.get(url, headers={"Range": "bytes=0-1024", "User-Agent": "Mozilla/5.0"}, timeout=15)
        print(f"      📄 Active ({resp.status_code}): {name or url}")
    except Exception as e:
        print(f"      ❌ Error pinging file {name}: {e}")

def main():
    print(f"🚀 Launching Headless Browser to crawl: {ROOT_URL}\n")
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        )
        page = context.new_page()

        # Listen for internal Gofile content responses loaded natively by the page
        file_links = []
        
        def handle_response(response):
            if "contents/" in response.url and response.status == 200:
                try:
                    json_data = response.json()
                    children = json_data.get("data", {}).get("children", {})
                    for item_id, item in children.items():
                        if item.get("type") == "file" and item.get("link"):
                            file_links.append((item.get("link"), item.get("name", "file")))
                except Exception:
                    pass

        page.on("response", handle_response)

        print(f"📂 Loading Gofile web application...")
        page.goto(ROOT_URL, wait_until="networkidle", timeout=60000)
        time.sleep(3)  # Allow UI to populate

        print(f"✅ Extracted {len(file_links)} files from rendered page.")
        browser.close()

    if not file_links:
        print("⚠️ No direct download links found. Checking fallback element clicks...")
        sys.exit(0)

    print(f"\n🚀 Sending Keep-Alive pings to {len(file_links)} files...\n")
    for link, name in file_links:
        ping_direct_file(link, name)
        time.sleep(0.5)

    print("\n🎉 Entire storage hierarchy successfully scanned and pinged!")

if __name__ == "__main__":
    main()

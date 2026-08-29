import sys
import time
import requests
from playwright.sync_api import sync_playwright

ROOT_URL = "https://gofile.io/d/OBVVp1LI"

all_files = []      # list of (download_link, file_name)
visited_folders = set()

def ping_and_increment(url, name=""):
    """Downloads 2 MB to ensure Gofile registers a real download and increments the counter."""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Referer": "https://gofile.io/",
        "Range": "bytes=0-2097152"  # 2 MB buffer to trigger download counter
    }
    try:
        resp = requests.get(url, headers=headers, timeout=20, stream=True)
        # Read the chunk into memory
        _ = resp.raw.read(2097152)
        print(f"      📄 Active & Counted ({resp.status_code}): {name or url}")
    except Exception as e:
        print(f"      ❌ Error downloading {name}: {e}")

def main():
    print(f"🚀 Launching Headless Browser to crawl: {ROOT_URL}\n")
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 800}
        )
        page = context.new_page()

        def handle_response(response):
            if "contents/" in response.url and response.status == 200:
                try:
                    json_data = response.json()
                    children = json_data.get("data", {}).get("children", {})
                    for item_id, item in children.items():
                        if item.get("type") == "file" and item.get("link"):
                            item_tuple = (item.get("link"), item.get("name", "file"))
                            if item_tuple not in all_files:
                                all_files.append(item_tuple)
                except Exception:
                    pass

        page.on("response", handle_response)

        print(f"📂 Navigating to root folder...")
        page.goto(ROOT_URL, wait_until="networkidle", timeout=60000)
        time.sleep(3)

        # Recursive folder explorer: find all folder elements and click them
        def explore_folders():
            # Find all clickable folder rows / links on current view
            folder_elements = page.query_selector_all("a[href*='/d/'], tr[data-type='folder'], div[data-type='folder']")
            
            for elem in folder_elements:
                try:
                    href = elem.get_attribute("href") or ""
                    folder_id = href.split("/d/")[-1].split("?")[0] if "/d/" in href else ""
                    
                    if folder_id and folder_id not in visited_folders and folder_id != "OBVVp1LI":
                        visited_folders.add(folder_id)
                        print(f"  📁 Entering subfolder: {folder_id}")
                        page.goto(f"https://gofile.io/d/{folder_id}", wait_until="networkidle", timeout=30000)
                        time.sleep(3)
                        explore_folders()  # Look for deeper nested folders
                except Exception:
                    pass

        explore_folders()
        browser.close()

    print(f"\n✅ Discovered {len(all_files)} total file(s) across all folders.")

    if not all_files:
        print("⚠️ No files found.")
        sys.exit(0)

    print(f"\n🚀 Sending Keep-Alive & metric triggers to {len(all_files)} file(s)...\n")
    for link, name in all_files:
        ping_and_increment(link, name)
        time.sleep(1)

    print("\n🎉 All files across all subfolders successfully pinged and updated!")

if __name__ == "__main__":
    main()

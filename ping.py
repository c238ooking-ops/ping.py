import sys
import time
import requests
from collections import deque
from playwright.sync_api import sync_playwright

ROOT_URL = "https://gofile.io/d/OBVVp1LI"

all_files = {}       # item_id -> (download_link, name)
folders_queue = deque(["OBVVp1LI"])
visited_folders = set()

def get_browser_session():
    """Launches browser briefly to capture live tokens and headers."""
    print("🌐 Extracting active session credentials from browser...")
    captured = {"token": None, "wt": None, "headers": {}}
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        )
        page = context.new_page()

        def intercept_request(request):
            if "contents/" in request.url:
                captured["headers"] = request.headers
                if "x-website-token" in request.headers:
                    captured["wt"] = request.headers["x-website-token"]
                if "authorization" in request.headers:
                    captured["token"] = request.headers["authorization"]

        page.on("request", intercept_request)
        page.goto(ROOT_URL, wait_until="networkidle", timeout=30000)
        time.sleep(2)
        browser.close()
        
    print("✅ Session credentials captured.\n")
    return captured

def ping_file(session, url, name=""):
    """Lightweight 256 KB chunk stream to reset file expiry."""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
        "Referer": "https://gofile.io/",
        "Range": "bytes=0-262144"
    }
    try:
        resp = session.get(url, headers=headers, timeout=10, stream=True)
        _ = resp.raw.read(262144)
        print(f"      📄 Active ({resp.status_code}): {name}")
    except Exception as e:
        print(f"      ❌ Error on {name}: {e}")

def main():
    session_data = get_browser_session()
    headers = session_data["headers"]
    
    http_session = requests.Session()
    http_session.headers.update(headers)

    print("🚀 Crawling folder hierarchy with full pagination...")
    
    while folders_queue:
        current_folder = folders_queue.popleft()
        if current_folder in visited_folders:
            continue
            
        visited_folders.add(current_folder)
        
        # Paginate through each folder until no more pages remain
        page_num = 1
        while True:
            api_url = f"https://api.gofile.io/contents/{current_folder}?page={page_num}&pageSize=20&sortField=createTime&sortDirection=-1"
            
            try:
                res = http_session.get(api_url, timeout=10).json()
                if res.get("status") != "ok":
                    print(f"  ⚠️ Error fetching folder [{current_folder}] page {page_num}: {res.get('status')}")
                    break

                data = res.get("data", {})
                children = data.get("children", {})
                
                # If page is empty, we reached the end of this folder
                if not children:
                    break

                for item_id, item in children.items():
                    if item.get("type") == "file" and item.get("link"):
                        all_files[item_id] = (item.get("link"), item.get("name", "file"))
                    elif item.get("type") == "folder":
                        if item_id not in visited_folders and item_id not in folders_queue:
                            folders_queue.append(item_id)

                # Check if we've fetched all items in this folder
                total_children = data.get("totalChildren", 0)
                total_pages = data.get("totalChildrenPages", 1)
                
                if page_num >= total_pages or len(children) == 0:
                    break
                    
                page_num += 1
                time.sleep(0.1)

            except Exception as e:
                print(f"  ⚠️ Exception on folder [{current_folder}] page {page_num}: {e}")
                break

    total_files = list(all_files.values())
    print(f"\n✅ Discovered {len(total_files)} total files across {len(visited_folders)} folders (Full Pagination Complete).")

    if not total_files:
        print("⚠️ No files found.")
        sys.exit(0)

    print(f"\n🚀 Sending Keep-Alive pings to {len(total_files)} file(s)...\n")
    for link, name in total_files:
        ping_file(http_session, link, name)
        time.sleep(0.1)

    print("\n🎉 Entire storage library kept alive!")

if __name__ == "__main__":
    main()

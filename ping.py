import sys
import time
import requests
from collections import deque
from playwright.sync_api import sync_playwright

ROOT_URL = "https://gofile.io/d/OBVVp1LI"

all_files = {}       # id -> (url, name)
folders_queue = deque([("OBVVp1LI", "Root Folder")])
visited_folders = set()

def get_browser_session():
    """Extracts live browser session headers and token."""
    print("🌐 Extracting active session credentials from browser...")
    captured = {"headers": {}}
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        )
        page = context.new_page()

        def intercept_request(request):
            if "contents/" in request.url:
                captured["headers"] = dict(request.headers)

        page.on("request", intercept_request)
        page.goto(ROOT_URL, wait_until="networkidle", timeout=30000)
        time.sleep(2)
        browser.close()
        
    print("✅ Session credentials captured.\n")
    return captured

def ping_file(session, url, name=""):
    """Pings a file to reset expiration."""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
        "Referer": "https://gofile.io/",
        "Range": "bytes=0-262144"  # 256 KB chunk
    }
    try:
        resp = session.get(url, headers=headers, timeout=12, stream=True)
        _ = resp.raw.read(262144)
        print(f"      📄 Active ({resp.status_code}): {name}")
    except Exception as e:
        print(f"      ❌ Error on {name}: {e}")

def main():
    session_data = get_browser_session()
    http_session = requests.Session()
    http_session.headers.update(session_data["headers"])

    print("🚀 Crawling root folder and all subfolders...\n")
    
    while folders_queue:
        current_folder_id, current_folder_name = folders_queue.popleft()
        if current_folder_id in visited_folders:
            continue
            
        visited_folders.add(current_folder_id)
        
        page_num = 1
        folder_found_files = 0
        folder_found_subfolders = 0

        while True:
            api_url = f"https://api.gofile.io/contents/{current_folder_id}?page={page_num}&pageSize=50&sortField=createTime&sortDirection=-1"
            
            try:
                res = http_session.get(api_url, timeout=12).json()
                if res.get("status") != "ok":
                    print(f"  ⚠️ Folder [{current_folder_name} ({current_folder_id})] returned status: {res.get('status')}")
                    break

                data = res.get("data", {})
                children = data.get("children", {})
                
                if not children:
                    break

                for item_id, item in children.items():
                    item_type = item.get("type", "")
                    item_name = item.get("name", item_id)
                    
                    if item_type == "folder":
                        folder_code = item.get("code") or item.get("id") or item_id
                        if folder_code not in visited_folders and all(folder_code != f[0] for f in folders_queue):
                            folders_queue.append((folder_code, item_name))
                            folder_found_subfolders += 1
                    else:
                        # Resilient download link extraction
                        dl_url = item.get("link") or item.get("directDownload") or item.get("downloadPage")
                        if not dl_url:
                            dl_url = f"https://api.gofile.io/contents/{item_id}"
                            
                        if item_id not in all_files:
                            all_files[item_id] = (dl_url, item_name)
                            folder_found_files += 1

                total_pages = data.get("totalChildrenPages", 1)
                if page_num >= total_pages or len(children) == 0:
                    break
                    
                page_num += 1
                time.sleep(0.05)

            except Exception as e:
                print(f"  ⚠️ Error parsing folder [{current_folder_name}]: {e}")
                break

        print(f"📂 [{current_folder_name}] ➜ {folder_found_files} file(s), {folder_found_subfolders} subfolder(s)")

    total_files = list(all_files.values())
    print(f"\n========================================================")
    print(f"✅ DISCOVERY COMPLETE: {len(total_files)} total files across {len(visited_folders)} folders")
    print(f"========================================================\n")

    if not total_files:
        print("⚠️ No files found to ping.")
        sys.exit(0)

    print(f"🚀 Pinging all {len(total_files)} files...\n")
    for link, name in total_files:
        ping_file(http_session, link, name)
        time.sleep(0.1)

    print("\n🎉 All files and folders successfully kept alive!")

if __name__ == "__main__":
    main()

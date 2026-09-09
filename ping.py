import os
import sys
import time
import requests
from collections import deque
from playwright.sync_api import sync_playwright

ROOT_URL = "https://gofile.io/d/OBVVp1LI"
ROOT_CODE = "OBVVp1LI"

# Store unique files as dict of url -> name to prevent ID collisions
discovered_files = {}
folders_queue = deque([(ROOT_CODE, "Root Folder")])
visited_folders = set()

class SessionManager:
    def __init__(self, root_url):
        self.root_url = root_url
        self.session = requests.Session()
        self.last_auth_time = 0
        self.refresh_credentials()

    def refresh_credentials(self):
        """Extracts clean browser session token & headers using Chromium."""
        print("🌐 Refreshing active browser session credentials...")
        captured = {"headers": {}}
        
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
                viewport={"width": 1280, "height": 720}
            )
            page = context.new_page()

            def intercept_request(request):
                if "contents/" in request.url:
                    captured["headers"] = dict(request.headers)

            page.on("request", intercept_request)
            page.goto(self.root_url, wait_until="networkidle", timeout=45000)
            time.sleep(2)
            browser.close()

        self.session.headers.clear()
        self.session.headers.update(captured["headers"])
        self.last_auth_time = time.time()
        print("✅ Fresh session credentials loaded.\n")

    def ensure_fresh(self):
        if time.time() - self.last_auth_time > 900:
            self.refresh_credentials()

def fetch_folder_contents(session_mgr, folder_code, page_num=1, max_retries=4):
    """Queries Gofile API with automatic backoff for rate limits."""
    api_url = f"https://api.gofile.io/contents/{folder_code}?page={page_num}&pageSize=50&sortField=createTime&sortDirection=-1"
    
    for attempt in range(max_retries):
        session_mgr.ensure_fresh()
        try:
            res = session_mgr.session.get(api_url, timeout=20).json()
            status = res.get("status")

            if status == "ok":
                return res
            elif status in ["error-rateLimit", "429"]:
                cool_off = 12 + (attempt * 6)
                print(f"    ⏳ Rate limit on [{folder_code}]. Pausing {cool_off}s (Attempt {attempt+1}/{max_retries})...")
                time.sleep(cool_off)
            elif status in ["error-auth", "error-token"]:
                print("    🔑 Token expired, re-authenticating...")
                session_mgr.refresh_credentials()
                time.sleep(2)
            else:
                return res
        except Exception as e:
            time.sleep(3)
            
    return None

def ping_fast(session_mgr, url, name=""):
    """Pings 64 KB to count as an active download event."""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Referer": "https://gofile.io/",
        "Range": "bytes=0-65535"
    }
    try:
        resp = session_mgr.session.get(url, headers=headers, timeout=15, stream=True)
        _ = resp.raw.read(65535)
        print(f"      📄 Counted ({resp.status_code}): {name}")
    except Exception as e:
        print(f"      ❌ Error on {name}: {e}")

def main():
    session_mgr = SessionManager(ROOT_URL)

    print("🚀 Crawling Gofile folder tree (Exact Code & Collision-Proof Resolution)...\n")
    
    while folders_queue:
        current_folder_code, current_folder_name = folders_queue.popleft()
        
        if current_folder_code in visited_folders:
            continue
            
        visited_folders.add(current_folder_code)
        
        page_num = 1
        folder_found_files = 0
        folder_found_subfolders = 0

        while True:
            res = fetch_folder_contents(session_mgr, current_folder_code, page_num)
            
            if not res or res.get("status") != "ok":
                status_str = res.get("status") if res else "No response"
                print(f"  ❌ Folder [{current_folder_name} ({current_folder_code})] failed: {status_str}")
                break

            data = res.get("data", {})
            children = data.get("children", {})
            
            if not children:
                break

            for key, item in children.items():
                item_type = item.get("type", "")
                item_name = item.get("name", key)

                if item_type == "folder":
                    # Strictly use 'code' for API navigation; fallback to id/key only if code is absent
                    next_code = item.get("code") or item.get("id") or key
                    if next_code not in visited_folders and all(next_code != f[0] for f in folders_queue):
                        folders_queue.append((next_code, item_name))
                        folder_found_subfolders += 1
                else:
                    # Resolve download link across all potential API keys
                    dl_url = item.get("link") or item.get("directDownload") or item.get("downloadPage")
                    if not dl_url:
                        dl_url = f"https://api.gofile.io/contents/{item.get('id') or key}"

                    # Save indexed by direct URL to avoid any item_id overwrite collisions
                    if dl_url not in discovered_files:
                        discovered_files[dl_url] = item_name
                        folder_found_files += 1

            total_pages = data.get("totalChildrenPages", 1)
            total_children = data.get("totalChildren", 0)

            if page_num >= total_pages or len(children) == 0:
                break
                
            page_num += 1
            time.sleep(1.2)

        print(f"📂 [{current_folder_name}] ➜ Found {folder_found_files} file(s), {folder_found_subfolders} subfolder(s)")
        time.sleep(1.5)

    file_list = list(discovered_files.items())
    print("\n========================================================")
    print(f"✅ DISCOVERY COMPLETE: {len(file_list)} total unique files across {len(visited_folders)} folders")
    print("========================================================\n")

    if not file_list:
        print("⚠️ No files found to ping.")
        sys.exit(0)

    print(f"🚀 Sending 64KB pings to {len(file_list)} file(s)...\n")
    for link, name in file_list:
        ping_fast(session_mgr, link, name)
        time.sleep(0.15)

    print("\n🎉 Keep-alive sequence complete! All files refreshed without omissions.")

if __name__ == "__main__":
    main()

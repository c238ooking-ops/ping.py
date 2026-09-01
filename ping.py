def ping_file(session_mgr, url, name=""):
    """Streams 10 MB without Range headers to trigger Gofile's activity counter."""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Referer": "https://gofile.io/",
        "Accept": "*/*"
    }
    try:
        # Full stream request (no Range header)
        with session_mgr.session.get(url, headers=headers, timeout=25, stream=True) as resp:
            if resp.status_code == 200:
                downloaded = 0
                target_bytes = 10 * 1024 * 1024  # Read 10 MB
                for chunk in resp.iter_content(chunk_size=1024 * 1024):
                    if chunk:
                        downloaded += len(chunk)
                        if downloaded >= target_bytes:
                            break
                print(f"      📄 Active & Counted (200 - {downloaded // (1024*1024)}MB): {name}")
            else:
                print(f"      ⚠️ Status {resp.status_code}: {name}")
    except Exception as e:
        print(f"      ❌ Error on {name}: {e}")

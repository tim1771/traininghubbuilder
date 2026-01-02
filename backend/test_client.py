import requests
import time

BASE_URL = "http://127.0.0.1:8000/api/browser"

def test_flow():
    print("0. Checking Root & Loop Policy...")
    try:
        root = requests.get("http://127.0.0.1:8000/")
        print("Root Response:", root.json())
    except:
        print("Root check failed")

    print("\n1. Launching Browser...")
    res = requests.post(f"{BASE_URL}/launch", json={"headless": True, "use_auth": False})
    print(res.json())
    if res.status_code != 200: return

    print("\n2. Navigating...")
    res = requests.post(f"{BASE_URL}/navigate", json={"url": "https://example.com"})
    print(res.json())
    if res.status_code != 200: return

    # Give it a sec to load
    time.sleep(2)

    print("\n3. Scraping...")
    res = requests.post(f"{BASE_URL}/scrape")
    print(res.json())
    
    if res.status_code == 200:
        print("\nSUCCESS: Scrape executed.")
    else:
        print("\nFAIL: Scrape error.")

if __name__ == "__main__":
    test_flow()

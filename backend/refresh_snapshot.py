import asyncio
from playwright.async_api import async_playwright
import json
import os
import time

async def refresh_snapshot():
    print("Launching browser for manual refresh...")
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.set_viewport_size({"width": 1280, "height": 720})
        
        url = "https://supabase.com"
        print(f"Navigating to {url}...")
        await page.goto(url)
        await page.wait_for_load_state("networkidle")
        await asyncio.sleep(2) # Extra wait for hydration

        # Ensure output dir
        os.makedirs("scraped_data", exist_ok=True)
        
        # Take FULL PAGE screenshot
        filename = f"screenshot_full_{int(time.time())}.png"
        filepath = os.path.join("scraped_data", filename)
        print(f"Capturing full-page screenshot to {filepath}...")
        await page.screenshot(path=filepath, full_page=True)
        
        # Extract elements matching backend logic
        interactive_elements = []
        selectors = ["a", "button", "input[type='button']", "input[type='submit']"]
        
        # Simple extraction logic mirroring the backend
        for selector in selectors:
            elements = await page.query_selector_all(selector)
            for el in elements:
                try:
                    if not await el.is_visible():
                        continue
                    box = await el.bounding_box()
                    if not box:
                        continue
                    
                    # Get text
                    text = await el.inner_text()
                    if not text:
                        text = await el.get_attribute("value") or await el.get_attribute("placeholder") or "unnamed"
                    
                    interactive_elements.append({
                        "text": text.strip(),
                        "type": selector,
                        "x": box["x"],
                        "y": box["y"], # These are relative to the top of the page, which works with full_page screenshot
                        "width": box["width"],
                        "height": box["height"]
                    })
                except:
                    continue

        data = {
            "title": await page.title(),
            "url": url,
            "text_content": "Manual Refresh Content",
            "screenshot": f"scraped_data/{filename}", # Relative path for frontend
            "viewport": {"width": 1280, "height": 720},
            "interactive_elements": interactive_elements[:100]
        }
        
        with open(os.path.join("scraped_data", "latest_scrape.json"), "w") as f:
            json.dump(data, f, indent=2)
            
        print("Snapshot updated successfully!")
        await browser.close()

if __name__ == "__main__":
    asyncio.run(refresh_snapshot())

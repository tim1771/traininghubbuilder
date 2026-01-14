import asyncio
import time
import os

class ContentExtractor:
    def __init__(self, output_dir="scraped_data"):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)

    async def extract_page(self, page, screenshot=True):
        """Detailed extraction of the current page including element coordinates."""
        from bs4 import BeautifulSoup
        
        # Wait for dynamic content
        await asyncio.sleep(2)
        
        title = await page.title()
        url = page.url
        content = await page.content()
        viewport = page.viewport_size or {"width": 1280, "height": 720}
        
        soup = BeautifulSoup(content, 'html.parser')
        for script in soup(["script", "style"]):
            script.decompose()
        text_content = soup.get_text(separator=' ', strip=True)
        
        screenshot_path = None
        if screenshot:
            filename = f"screenshot_{int(time.time())}.png"
            screenshot_path = os.path.join(self.output_dir, filename)
            await page.screenshot(path=screenshot_path)

        # Extract interactive elements with coordinates
        interactive_elements = []
        selectors = ["a", "button", "input[type='button']", "input[type='submit']"]
        for selector in selectors:
            elements = await page.query_selector_all(selector)
            for el in elements:
                try:
                    if not await el.is_visible():
                        continue
                    box = await el.bounding_box()
                    if not box:
                        continue
                    text = (await el.inner_text()).strip() or await el.get_attribute("value") or await el.get_attribute("placeholder") or "unnamed"
                    interactive_elements.append({
                        "text": text,
                        "type": selector,
                        "x": box["x"],
                        "y": box["y"],
                        "width": box["width"],
                        "height": box["height"]
                    })
                except:
                    continue

        return {
            "title": title,
            "url": url,
            "text_content": text_content,
            "screenshot": screenshot_path,
            "viewport": viewport,
            "interactive_elements": interactive_elements[:100]
        }

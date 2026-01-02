from playwright.async_api import Page
from bs4 import BeautifulSoup
import time
import os

class ContentExtractor:
    def __init__(self, output_dir="scraped_data"):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)

    async def extract_page(self, page: Page, screenshot=True):
        """detailed extraction of the current page."""
        title = await page.title()
        url = page.url
        content = await page.content()
        
        # Parse text with BS4 for cleaner output than innerText
        soup = BeautifulSoup(content, 'html.parser')
        
        # Remove scripts and styles
        for script in soup(["script", "style"]):
            script.decompose()
            
        text_content = soup.get_text(separator=' ', strip=True)
        
        screenshot_path = None
        if screenshot:
            filename = f"screenshot_{int(time.time())}.png"
            screenshot_path = os.path.join(self.output_dir, filename)
            await page.screenshot(path=screenshot_path)

        # Extract links for navigation
        links = []
        for a in soup.find_all('a', href=True):
            links.append({'text': a.get_text(strip=True), 'href': a['href']})

        return {
            "title": title,
            "url": url,
            "text_content": text_content,
            "screenshot": screenshot_path,
            "links": links[:50] # Limit links to avoid overflow
        }

from playwright.async_api import async_playwright
import asyncio

class BrowserManager:
    def __init__(self):
        self.playwright = None
        self.browser = None
        self.context = None
        self.page = None

    async def launch(self, headless=False, auth_state_path=None):
        """Launches the browser instance."""
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(headless=headless)
        
        context_args = {
            'viewport': {'width': 1280, 'height': 720},
            'user_agent': "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        
        if auth_state_path:
            import os
            if os.path.exists(auth_state_path):
                context_args['storage_state'] = auth_state_path
                print(f"Loading auth state from {auth_state_path}")

        self.context = await self.browser.new_context(**context_args)
        self.page = await self.context.new_page()
        return self.page

    async def close(self):
        """Cleans up resources."""
        if self.context:
            await self.context.close()
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()

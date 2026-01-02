from playwright.async_api import BrowserContext
import json
import os

class AuthManager:
    def __init__(self, storage_path="auth_state.json"):
        self.storage_path = os.path.abspath(storage_path)

    async def save_state(self, context: BrowserContext):
        """Saves storage state to file."""
        await context.storage_state(path=self.storage_path)
        print(f"State saved to {self.storage_path}")
        return self.storage_path

    def exists(self):
        return os.path.exists(self.storage_path)

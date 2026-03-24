"""
Test script to verify Playwright-based inbox scraping.
Run from the backend directory: uv run python test_messaging_api.py
"""

import asyncio

from app.services.linkedin_browser import LinkedInBrowser


async def main():
    print("Starting browser...")
    async with LinkedInBrowser() as browser:
        is_logged = await browser.is_logged_in()
        print(f"Logged in: {is_logged}")
        if not is_logged:
            print("Not logged in. Run test_auth.py first.")
            return

        # Scrape conversations
        print("\nScraping inbox conversations...")
        conversations = await browser.scrape_inbox_conversations(max_items=10)

        print(f"\nFound {len(conversations)} conversations:\n")
        for i, conv in enumerate(conversations):
            print(f"  {i+1}. {conv['participant_name']}")
            print(f"     Preview: {conv['last_message_preview'][:80]}")
            print(f"     Time: {conv['timestamp_text']}")
            print()

    print("Done!")


if __name__ == "__main__":
    asyncio.run(main())

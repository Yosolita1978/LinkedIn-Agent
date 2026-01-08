import asyncio
from pathlib import Path
from app.services.linkedin_browser import LinkedInBrowser


async def main():
    async with LinkedInBrowser() as browser:
        if not await browser.is_logged_in():
            print("Not logged in. Run manual login first.")
            return

        # Test connections
        print("Scraping connections...")
        connections = await browser.scrape_connections()
        print(f"Found {len(connections)} connections")

        # Test followers
        print("\nScraping followers...")
        followers = await browser.scrape_followers()

        if followers:
            print(f"Found {len(followers)} followers:\n")
            for f in followers[:5]:
                print(f"  {f['name']}")
                print(f"    {f['headline']}")
                print(f"    {f['profile_url']}\n")
        else:
            # Debug: save HTML if no followers found
            print("No followers found. Saving debug HTML...")
            debug_dir = Path("playwright-data")
            html = await browser.page.content()
            with open(debug_dir / "followers_debug.html", "w") as f:
                f.write(html)
            await browser.page.screenshot(path=debug_dir / "followers_debug.png", full_page=True)
            print(f"Saved debug files to {debug_dir}/")


if __name__ == "__main__":
    asyncio.run(main())
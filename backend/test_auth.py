import asyncio
import logging
from app.services.linkedin_browser import LinkedInBrowser

# Enable logging output
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)


async def main():
    async with LinkedInBrowser() as browser:
        if not await browser.is_logged_in():
            print("Not logged in. Starting manual login...")
            success = await browser.manual_login()
            if not success:
                print("Login failed. Exiting.")
                return
            print("Login successful! Cookies saved.\n")

        # Test connections with pagination (max 50)
        print("\nScraping connections (max 50)...")
        connections = await browser.scrape_connections(max_items=50)
        print(f"\nFound {len(connections)} connections total")

        if connections:
            print("\nFirst 5 connections:")
            for c in connections[:5]:
                print(f"  {c['name']}")
                print(f"    {c['profile_url']}\n")

            # Test profile scraping on the first connection
            print("\n" + "=" * 50)
            print("Testing profile detail extraction...")
            print("=" * 50)

            first_profile_url = connections[0]["profile_url"]
            print(f"\nScraping profile: {first_profile_url}")

            profile = await browser.scrape_profile(first_profile_url)

            if profile:
                print(f"\nProfile Details:")
                print(f"  Name: {profile.get('name', 'N/A')}")
                print(f"  Headline: {profile.get('headline', 'N/A')}")
                print(f"  Location: {profile.get('location', 'N/A')}")
                print(f"  Company: {profile.get('company', 'N/A')}")
                print(f"  About: {profile.get('about', 'N/A')[:100]}...")

                if profile.get('experience'):
                    print(f"\n  Experience ({len(profile['experience'])} entries):")
                    for exp in profile['experience'][:3]:
                        print(f"    - {exp['title']} at {exp['company']}")

                if profile.get('education'):
                    print(f"\n  Education ({len(profile['education'])} entries):")
                    for edu in profile['education']:
                        print(f"    - {edu['school']}: {edu['degree']}")
            else:
                print("Failed to scrape profile")


if __name__ == "__main__":
    asyncio.run(main())

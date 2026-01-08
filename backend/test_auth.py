import asyncio
from app.services.linkedin_browser import LinkedInBrowser


async def main():
    async with LinkedInBrowser() as browser:
        if await browser.is_logged_in():
            print("Already logged in!")
        else:
            print("Not logged in. Starting manual login...")
            success = await browser.manual_login()
            print(f"Login result: {success}")


if __name__ == "__main__":
    asyncio.run(main())
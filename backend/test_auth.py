import asyncio
import logging
from collections import Counter

from app.services.linkedin_browser import LinkedInBrowser, ScrapingError
from app.services.linkedin_voyager import LinkedInVoyager

# Enable logging output
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)


async def main():
    # Step 1: verify the LinkedIn session (manual login only if needed).
    async with LinkedInBrowser() as browser:
        if not await browser.is_logged_in():
            print("Not logged in. Starting manual login...")
            success = await browser.manual_login()
            if not success:
                print("Login failed. Exiting.")
                return
            print("Login successful! Cookies saved.\n")
        else:
            print("Already logged in — existing session/cookies are valid.\n")

        # Step 2: scrape a small batch of followers (name + url only; the
        # followers page has no degree badge).
        print("Scraping followers (max 10)...")
        try:
            followers = await browser.scrape_followers(max_items=10)
        except ScrapingError as e:
            print(f"\nFollower scrape failed: {e}")
            print("Your session is still valid — this is a page-structure issue, "
                  "not an auth problem.")
            return

    print(f"\nFound {len(followers)} followers in this batch.")
    if not followers:
        print("No follower cards were read.")
        return

    # Step 3: enrich via Voyager to get the connection degree + company. This is
    # how the scan decides who is a candidate:
    #   DISTANCE_1 -> already connected (excluded)
    #   DISTANCE_2/3 -> follower-not-connection (a candidate)
    #   ''  -> degree could not be determined (skipped, reported as an error)
    print("Enriching via Voyager (degree + company)...\n")
    voyager = LinkedInVoyager()
    await voyager.start()
    if not await voyager.is_authenticated():
        print("Voyager not authenticated — cannot classify by degree.")
        await voyager.stop()
        return

    degree_counts: Counter = Counter()
    candidates = 0
    for f in followers:
        profile = await voyager.get_profile(f["profile_url"])
        degree = (profile or {}).get("connection_degree", "") or "unknown"
        company = (profile or {}).get("company", "")
        degree_counts[degree] += 1
        if degree in ("DISTANCE_2", "DISTANCE_3"):
            candidates += 1
        print(f"  {f['name']:25} {degree:12} {company}")

    await voyager.stop()

    print("\nDegree breakdown:")
    for degree, count in sorted(degree_counts.items()):
        print(f"  {degree}: {count}")
    print(
        f"\n{candidates} of {len(followers)} are connection candidates "
        f"(2nd/3rd degree, not yet connected)."
    )


if __name__ == "__main__":
    asyncio.run(main())

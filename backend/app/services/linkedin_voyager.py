"""
LinkedIn Voyager API Client

Calls LinkedIn's internal REST API directly using stored cookies.
~10-15x faster than Playwright DOM scraping (~1s vs ~10-15s per profile).

Usage:
    voyager = LinkedInVoyager()  # reads cookies from playwright-data/cookies.json
    profile = await voyager.get_profile("https://www.linkedin.com/in/john-doe-123")
"""

import json
import logging
import re
from pathlib import Path
from urllib.parse import quote

import httpx

logger = logging.getLogger(__name__)

VOYAGER_BASE = "https://www.linkedin.com/voyager/api"

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)

# Decoration IDs tell the Voyager API what data to return
PROFILE_DECORATION = (
    "com.linkedin.voyager.dash.deco.identity.profile."
    "TopCardSupplementary-163"
)


def extract_profile_id(profile_url: str) -> str:
    """
    Extract the profile identifier from a LinkedIn URL.
    Can be a vanity name (john-doe-123) or an encoded member ID (ACoAAA...).
    """
    match = re.search(r"linkedin\.com/in/([^/?#]+)", profile_url)
    if match:
        return match.group(1).strip("/")
    raise ValueError(f"Cannot extract profile ID from URL: {profile_url}")


def is_encoded_member_id(profile_id: str) -> bool:
    """
    Check if a profile ID is an encoded member URN (e.g. ACoAAAfvSjYB...)
    vs a human-readable vanity name (e.g. john-doe-123).

    Encoded IDs start with 'ACo' and are base64-like strings.
    Vanity names contain lowercase letters, numbers, and hyphens.
    """
    return profile_id.startswith("ACo") or profile_id.startswith("urn:")


class LinkedInVoyager:
    """Fast LinkedIn profile fetcher using the Voyager API."""

    def __init__(self, cookies_path: Path | None = None):
        if cookies_path is None:
            cookies_path = Path(__file__).parents[2] / "playwright-data" / "cookies.json"
        self._cookies_path = cookies_path
        self._client: httpx.AsyncClient | None = None
        self._headers: dict = {}

    async def start(self) -> None:
        """Load cookies and create HTTP client."""
        li_at, jsessionid = self._read_cookies()
        csrf_token = jsessionid.strip('"')

        self._headers = {
            "csrf-token": csrf_token,
            "cookie": f"li_at={li_at}; JSESSIONID={jsessionid}",
            "user-agent": USER_AGENT,
            "accept": "application/vnd.linkedin.normalized+json+2.1",
            "x-li-lang": "en_US",
            "x-restli-protocol-version": "2.0.0",
        }

        self._client = httpx.AsyncClient(
            headers=self._headers,
            timeout=15.0,
            follow_redirects=True,
        )
        logger.info("Voyager API client started")

    async def stop(self) -> None:
        """Close HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None

    async def __aenter__(self) -> "LinkedInVoyager":
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        await self.stop()

    def _read_cookies(self) -> tuple[str, str]:
        """Read li_at and JSESSIONID from the cookies file."""
        if not self._cookies_path.exists():
            raise FileNotFoundError(
                f"Cookies file not found: {self._cookies_path}. "
                "Run test_auth.py first to authenticate."
            )

        with open(self._cookies_path, "r") as f:
            cookies = json.load(f)

        li_at = None
        jsessionid = None

        for cookie in cookies:
            name = cookie.get("name", "")
            if name == "li_at":
                li_at = cookie["value"]
            elif name == "JSESSIONID":
                jsessionid = cookie["value"]

        if not li_at or not jsessionid:
            raise ValueError(
                "Missing li_at or JSESSIONID in cookies. "
                "Re-authenticate with test_auth.py."
            )

        return li_at, jsessionid

    async def is_authenticated(self) -> bool:
        """Check if the current cookies are still valid."""
        try:
            resp = await self._client.get(f"{VOYAGER_BASE}/me")
            return resp.status_code == 200
        except Exception as e:
            logger.error(f"Auth check failed: {e}")
            return False

    async def get_profile(self, profile_url: str) -> dict | None:
        """
        Fetch profile data via the Voyager API.

        Handles both vanity names (john-doe-123) and encoded member IDs (ACoAAA...).
        Tries multiple Voyager endpoints until one works.
        """
        try:
            profile_id = extract_profile_id(profile_url)
        except ValueError as e:
            logger.error(str(e))
            return None

        logger.info(f"Voyager: fetching {profile_id[:30]}...")

        # Try endpoints in order of reliability
        result = None

        if is_encoded_member_id(profile_id):
            # Encoded member ID — use the dash/profiles endpoint
            result = await self._fetch_by_member_id(profile_id)
            # If that fails, try the miniProfile endpoint
            if not result:
                result = await self._fetch_miniprofile(profile_id)
        else:
            # Vanity name — use the classic profileView endpoint
            result = await self._fetch_by_vanity(profile_id)
            # If that fails, try dash/profiles
            if not result:
                result = await self._fetch_by_member_id(profile_id)

        if result:
            result["profile_url"] = profile_url

        return result

    async def _fetch_by_vanity(self, vanity: str) -> dict | None:
        """Fetch profile using the classic profileView endpoint (vanity names only)."""
        url = f"{VOYAGER_BASE}/identity/profiles/{vanity}/profileView"

        try:
            resp = await self._client.get(url)
            if resp.status_code != 200:
                logger.debug(f"Voyager profileView: HTTP {resp.status_code} for {vanity}")
                return None
            return self._parse_profile_view(resp.json())
        except Exception as e:
            logger.debug(f"Voyager profileView error: {e}")
            return None

    async def _fetch_by_member_id(self, member_id: str) -> dict | None:
        """
        Fetch profile using the dash/profiles endpoint.
        Works with both vanity names and encoded member IDs.
        """
        url = f"{VOYAGER_BASE}/identity/dash/profiles"
        params = {
            "q": "memberIdentity",
            "memberIdentity": member_id,
            "decorationId": PROFILE_DECORATION,
        }

        try:
            resp = await self._client.get(url, params=params)
            if resp.status_code != 200:
                logger.debug(f"Voyager dash/profiles: HTTP {resp.status_code} for {member_id[:30]}")
                return None
            return self._parse_dash_profile(resp.json())
        except Exception as e:
            logger.debug(f"Voyager dash/profiles error: {e}")
            return None

    async def _fetch_miniprofile(self, member_id: str) -> dict | None:
        """
        Fetch basic profile info using the miniProfiles endpoint.
        Returns less data but works reliably with encoded member IDs.
        """
        urn = f"urn:li:fs_miniProfile:{member_id}"
        encoded_urn = quote(urn, safe="")
        url = f"{VOYAGER_BASE}/identity/miniProfiles/{encoded_urn}"

        try:
            resp = await self._client.get(url)
            if resp.status_code != 200:
                logger.debug(f"Voyager miniProfiles: HTTP {resp.status_code} for {member_id[:30]}")
                return None
            return self._parse_mini_profile(resp.json())
        except Exception as e:
            logger.debug(f"Voyager miniProfiles error: {e}")
            return None

    # ── Response Parsers ──

    def _parse_profile_view(self, data: dict) -> dict | None:
        """Parse the /identity/profiles/{id}/profileView response."""
        profile = self._empty_profile()

        included = data.get("included", [])
        if not included:
            return None

        for entity in included:
            entity_type = entity.get("$type", "")
            self._extract_from_entity(entity, entity_type, profile)

        return profile if profile["name"] else None

    def _parse_dash_profile(self, data: dict) -> dict | None:
        """Parse the /identity/dash/profiles response."""
        profile = self._empty_profile()

        # The dash endpoint can have data at the top level or in "included"
        included = data.get("included", [])
        elements = data.get("elements", [])

        # Try elements first (direct response)
        for element in elements:
            self._extract_from_entity(element, element.get("$type", ""), profile)

        # Then try included (normalized response)
        for entity in included:
            entity_type = entity.get("$type", "")
            self._extract_from_entity(entity, entity_type, profile)

        return profile if profile["name"] else None

    def _parse_mini_profile(self, data: dict) -> dict | None:
        """Parse the /identity/miniProfiles response (basic info only)."""
        profile = self._empty_profile()

        # Mini profile has direct fields
        first_name = data.get("firstName", "")
        last_name = data.get("lastName", "")
        if first_name or last_name:
            profile["name"] = f"{first_name} {last_name}".strip()

        profile["headline"] = data.get("occupation", "") or data.get("headline", "")

        # Location from entityLocale or backgroundImage metadata
        if data.get("locationName"):
            profile["location"] = data["locationName"]

        # Try to get company from occupation/headline
        occupation = data.get("occupation", "")
        if " at " in occupation:
            profile["company"] = occupation.split(" at ", 1)[1].strip()

        return profile if profile["name"] else None

    def _empty_profile(self) -> dict:
        """Return an empty profile template."""
        return {
            "name": "",
            "headline": "",
            "location": "",
            "about": "",
            "company": "",
            "experience": [],
            "education": [],
            "profile_url": "",
        }

    def _extract_from_entity(self, entity: dict, entity_type: str, profile: dict) -> None:
        """Extract profile data from a single Voyager entity into the profile dict."""

        # Profile / MiniProfile entities
        if any(t in entity_type for t in ["Profile", "MiniProfile"]):
            # Name
            first = entity.get("firstName", "")
            last = entity.get("lastName", "")
            if (first or last) and not profile["name"]:
                profile["name"] = f"{first} {last}".strip()

            # Headline
            headline = entity.get("headline", "") or entity.get("occupation", "")
            if headline and not profile["headline"]:
                profile["headline"] = headline

            # About/Summary
            summary = entity.get("summary", "")
            if summary and not profile["about"]:
                profile["about"] = summary[:500]

            # Location
            location = (
                entity.get("locationName", "")
                or entity.get("geoLocationName", "")
                or entity.get("geoLocation", {}).get("defaultLocalizedName", "")
            )
            if location and not profile["location"]:
                profile["location"] = location

        # Position entities (experience)
        if any(t in entity_type for t in ["Position", "position"]):
            title = entity.get("title", "")
            company = entity.get("companyName", "") or entity.get("company", {}).get("name", "")
            if title:
                profile["experience"].append({"title": title, "company": company})
                if company and not profile["company"]:
                    profile["company"] = company

        # Education entities
        if any(t in entity_type for t in ["Education", "education"]):
            school = entity.get("schoolName", "") or entity.get("school", {}).get("name", "")
            degree = entity.get("degreeName", "")
            field = entity.get("fieldOfStudy", "")
            degree_str = f"{degree}, {field}" if degree and field else degree or field
            if school:
                profile["education"].append({"school": school, "degree": degree_str})

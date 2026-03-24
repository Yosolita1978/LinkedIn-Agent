"""
Auth status routes — check LinkedIn cookie validity.
"""

import logging
from pathlib import Path

from fastapi import APIRouter

from app.services.linkedin_voyager import LinkedInVoyager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.get("/status")
async def auth_status():
    """
    Check if LinkedIn cookies (li_at + JSESSIONID) are still valid.

    Returns:
        - cookies_valid: whether the Voyager API responds successfully
        - cookies_found: whether the cookies file exists and has required cookies
        - message: human-readable status
    """
    cookies_path = Path(__file__).parents[2] / "playwright-data" / "cookies.json"

    # Check if cookies file exists
    if not cookies_path.exists():
        return {
            "cookies_valid": False,
            "cookies_found": False,
            "message": "Cookies file not found. Run test_auth.py to authenticate.",
        }

    # Try to create a Voyager client and check auth
    try:
        voyager = LinkedInVoyager(cookies_path=cookies_path)
        await voyager.start()
        try:
            is_valid = await voyager.is_authenticated()
            if is_valid:
                return {
                    "cookies_valid": True,
                    "cookies_found": True,
                    "message": "LinkedIn cookies are valid.",
                }
            else:
                return {
                    "cookies_valid": False,
                    "cookies_found": True,
                    "message": "LinkedIn cookies have expired. Re-authenticate with test_auth.py.",
                }
        finally:
            await voyager.stop()
    except ValueError as e:
        # Missing li_at or JSESSIONID in the file
        return {
            "cookies_valid": False,
            "cookies_found": False,
            "message": str(e),
        }
    except Exception as e:
        logger.error(f"Auth check error: {e}")
        return {
            "cookies_valid": False,
            "cookies_found": True,
            "message": f"Could not verify cookies: {e}",
        }
